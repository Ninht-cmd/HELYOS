"""GitHub open-source lab agent: read-only catalogue/clone status."""

from __future__ import annotations

from typing import Any

from ..governance.autonomy import AutonomyLevel
from ..governance.policy import Action, ActionType, Decision
from ..governance.service import GovernanceService
from ..integrations.open_source_lab import OpenSourceLab
from .base import Agent


class OpenSourceLabAgent(Agent):
    name = "open_source_lab"
    description = "Lit l'etat local du lab GitHub open source general (A0, lecture seule)."
    required_level = AutonomyLevel.A0

    def __init__(self, lab: OpenSourceLab | None = None) -> None:
        self.lab = lab or OpenSourceLab()

    def propose(self, context: dict[str, Any]) -> Action:
        return Action(
            type=ActionType.READ,
            description="Lire l'etat local du lab GitHub open source",
            target=str(context.get("target", self.lab.root)),
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
