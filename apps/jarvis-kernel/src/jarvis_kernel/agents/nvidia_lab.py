"""NVIDIA Lab agent.

This agent is deliberately read-only: it exposes the local NVIDIA lab state to
HELYOS/Jarvis without launching downloads, spending money, signing licences, or
touching external systems.
"""

from __future__ import annotations

from typing import Any

from ..governance.autonomy import AutonomyLevel
from ..governance.policy import Action, ActionType, Decision
from ..governance.service import GovernanceService
from ..integrations.nvidia_lab import NvidiaLab
from .base import Agent


class NvidiaLabAgent(Agent):
    name = "nvidia_lab"
    description = "Lit l'etat local du lab NVIDIA/CUDA/Hugging Face/GitHub (A0, lecture seule)."
    required_level = AutonomyLevel.A0

    def __init__(self, lab: NvidiaLab | None = None) -> None:
        self.lab = lab or NvidiaLab()

    def propose(self, context: dict[str, Any]) -> Action:
        target = str(context.get("target", self.lab.root))
        return Action(
            type=ActionType.READ,
            description="Lire l'etat local du lab NVIDIA",
            target=target,
            actor=self.name,
        )

    def snapshot(
        self,
        governance: GovernanceService,
        granted: AutonomyLevel = AutonomyLevel.A0,
    ) -> tuple[Any, dict | None]:
        verdict = governance.submit(self.propose({}), granted)
        if verdict.decision is not Decision.ALLOW:
            return verdict, None
        return verdict, self.lab.status()
