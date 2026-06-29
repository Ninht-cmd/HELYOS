"""Orchestrateur d'agents — composition gouvernée (RFC-0004).

Exécute une séquence d'étapes (un agent + un contexte). **Chaque étape passe par la
gouvernance** avant toute exécution : c'est la composition d'agents (ADN 9) placée sous
l'autorité du kernel. Léger et sans dépendance ; conçu pour être remplacé/enveloppé par
LangGraph (graphes) ou le NeMo Agent Toolkit (interop) sans changer ce contrat.

Politique d'arrêt : par défaut, l'orchestrateur **s'arrête** dès qu'une étape n'est pas
ALLOW (une action en attente de validation suspend la chaîne — sûr par défaut).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..governance.autonomy import AutonomyLevel
from ..governance.policy import Action, Decision, PolicyVerdict
from ..governance.service import GovernanceService
from ..observability.tracing import span
from .base import Agent


@dataclass(frozen=True)
class Step:
    agent: Agent
    context: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class StepResult:
    agent: str
    action: Action
    verdict: PolicyVerdict

    @property
    def allowed(self) -> bool:
        return self.verdict.allowed


class Orchestrator:
    def __init__(self, governance: GovernanceService) -> None:
        self.governance = governance

    def run(
        self,
        steps: list[Step],
        granted: AutonomyLevel,
        stop_on_block: bool = True,
    ) -> list[StepResult]:
        """Exécute les étapes sous gouvernance. Retourne la trace des verdicts."""
        results: list[StepResult] = []
        with span("orchestrator.run", **{"helyos.steps": len(steps)}):
            for step in steps:
                action = step.agent.propose(step.context)
                verdict = self.governance.submit(action, granted)
                results.append(StepResult(step.agent.name, action, verdict))
                if stop_on_block and verdict.decision is not Decision.ALLOW:
                    self.governance.bus.emit(
                        "orchestrator.halted",
                        at=step.agent.name,
                        decision=verdict.decision.value,
                    )
                    break
            else:
                self.governance.bus.emit("orchestrator.completed", steps=len(results))
        return results
