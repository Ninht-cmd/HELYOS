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
            # Prompt contraint : sans quoi un modèle 8B déroule son template
            # « ### 1. Compréhension du sujet » même sur une question ambiguë —
            # du vide verbeux constaté en réel dans le chat (2026-07-09).
            from ..persona import FOUNDER_PROMPT

            finding = self.llm.complete(
                f"{FOUNDER_PROMPT}\n\n"
                "Réponds à la demande ci-dessous en prose simple : pas de titres, pas de ###, "
                "pas de gras, pas de liste, 120 mots maximum. Si la demande est ambiguë ou "
                "renvoie à un contexte que tu n'as pas, dis-le en UNE phrase et pose UNE "
                "question de clarification — n'analyse jamais la formulation de la question. "
                "N'invente ni chiffre ni fait.\n\n"
                f"Demande : {topic}\nRéponse :",
                num_predict=220,
            )
            if memory is not None:
                memory.remember(topic, finding, namespace="research")
            governance.bus.emit("research.finding", topic=topic)
            return verdict, finding
