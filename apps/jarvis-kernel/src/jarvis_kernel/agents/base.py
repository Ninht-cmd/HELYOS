"""Contrat d'agent et registre.

Un agent ne *fait* rien directement : il **propose** une Action, qui est ensuite
soumise à la gouvernance. Il déclare le niveau d'autonomie qu'il requiert au
maximum (transparence — le registre permet d'auditer qui peut quoi).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from ..governance.autonomy import AutonomyLevel
from ..governance.policy import Action


class Agent(ABC):
    """Contrat minimal d'un agent."""

    #: Identifiant unique de l'agent.
    name: str = "agent"
    #: Description courte de sa fonction.
    description: str = ""
    #: Niveau d'autonomie maximal que cet agent peut requérir.
    required_level: AutonomyLevel = AutonomyLevel.A1

    @abstractmethod
    def propose(self, context: dict[str, Any]) -> Action:
        """À partir d'un contexte, propose une Action (non encore exécutée)."""
        ...

    def describe(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "required_level": self.required_level.name,
            "required_level_label": self.required_level.label,
        }


class ObserverAgent(Agent):
    """Agent d'exemple, purement observateur (A0). Ne propose que des lectures.

    Démontre le principe : un agent de perception n'a besoin que de A0 et ne peut,
    par construction, proposer que des actions de type READ.
    """

    name = "observer"
    description = "Observe et lit le contexte. N'agit jamais (A0)."
    required_level = AutonomyLevel.A0

    def propose(self, context: dict[str, Any]) -> Action:
        from ..governance.policy import ActionType

        target = str(context.get("target", "contexte courant"))
        return Action(
            type=ActionType.READ,
            description=f"Lire {target}",
            target=target,
            actor=self.name,
        )


class AgentRegistry:
    """Registre des agents disponibles."""

    def __init__(self) -> None:
        self._agents: dict[str, Agent] = {}

    def register(self, agent: Agent) -> Agent:
        if agent.name in self._agents:
            raise ValueError(f"Agent déjà enregistré : {agent.name!r}")
        self._agents[agent.name] = agent
        return agent

    def get(self, name: str) -> Agent | None:
        return self._agents.get(name)

    def list(self) -> list[Agent]:
        return list(self._agents.values())

    def __len__(self) -> int:
        return len(self._agents)

    def __contains__(self, name: object) -> bool:
        return name in self._agents
