"""ResearchAgent — agent d'analyse (A1), à composer avec d'autres.

Démontre l'intelligence composée (ADN 9) : il *analyse* (niveau A1, ne fait qu'orienter
et proposer) via un LLMPort, et range sa trouvaille en mémoire. Combiné au Scribe (A2),
on obtient une chaîne « analyser → décider → tracer » entièrement gouvernée.
"""

from __future__ import annotations

from typing import Any

from ..governance.autonomy import AutonomyLevel
from ..governance.policy import Action, ActionType, Decision
from ..governance.service import GovernanceService
from ..memory.store import MemoryStore
from ..observability.tracing import span
from .base import Agent
from .llm import LLMPort, StubLLM


class ResearchAgent(Agent):
    name = "research"
    description = "Analyse un sujet et propose une synthèse (A1, ne fait qu'orienter)."
    required_level = AutonomyLevel.A1

    def __init__(self, llm: LLMPort | None = None) -> None:
        self.llm = llm or StubLLM()

    def propose(self, context: dict[str, Any]) -> Action:
        topic = str(context.get("topic", "sujet non précisé"))
        return Action(
            type=ActionType.ANALYZE,
            description=f"Analyser : {topic}",
            actor=self.name,
        )

    def analyze(
        self,
        governance: GovernanceService,
        topic: str,
        granted: AutonomyLevel = AutonomyLevel.A1,
        memory: MemoryStore | None = None,
    ) -> tuple[Any, str | None]:
        """Soumet l'analyse à la gouvernance ; si autorisée, produit et mémorise une synthèse."""
        with span("research.analyze", **{"helyos.topic": topic}):
            verdict = governance.submit(self.propose({"topic": topic}), granted)
            if verdict.decision is not Decision.ALLOW:
                return verdict, None
            finding = self.llm.complete(f"Analyse concise et structurée du sujet : {topic}")
            if memory is not None:
                memory.remember(topic, finding, namespace="research")
            governance.bus.emit("research.finding", topic=topic)
            return verdict, finding
