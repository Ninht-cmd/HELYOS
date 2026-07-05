"""InvoiceReminderAgent — HELYOS v1 : automatiser UNE tâche payante (relance de factures).

Conforme au brief fondateur : un seul agent, une seule tâche, fiabilisable, local, zéro
coût d'API (Ollama), gouverné. Entrée = factures impayées ; sortie = relances rédigées.

Gouvernance honnête : rédiger les relances = A1 (préparation, aucun effet monde). ENVOYER
= action externe sensible → GR-2 : validation humaine obligatoire (le fondateur relit avant
que ça parte). HELYOS rédige et propose ; l'humain valide l'envoi.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..governance.autonomy import AutonomyLevel
from ..governance.policy import Action, ActionType, Decision
from ..governance.service import GovernanceService
from ..memory.store import MemoryStore
from ..observability.tracing import span
from .base import Agent
from .llm import LLMPort, StubLLM


@dataclass(frozen=True)
class Invoice:
    client: str
    amount_eur: float
    days_late: int
    email: str = ""
    ref: str = ""


@dataclass(frozen=True)
class Reminder:
    ref: str
    client: str
    email: str
    tone: str          # 'courtois' | 'ferme' | 'dernier_rappel'
    subject: str
    body: str


def _tone_for(days_late: int) -> str:
    if days_late <= 15:
        return "courtois"
    if days_late <= 45:
        return "ferme"
    return "dernier_rappel"


_TONE_BRIEF = {
    "courtois": "ton courtois et bienveillant, simple rappel amical",
    "ferme": "ton ferme mais professionnel, rappel des délais convenus",
    "dernier_rappel": "ton sérieux et formel, dernier rappel avant procédure "
                      "(NE PAS envoyer de mise en demeure automatique — le fondateur valide)",
}


class InvoiceReminderAgent(Agent):
    name = "invoice_reminder"
    description = "Rédige des relances de factures (A1) ; l'ENVOI passe par la gouvernance (A2/GR-2)."
    required_level = AutonomyLevel.A1

    def __init__(self, llm: LLMPort | None = None, sender_name: str = "[Votre nom]") -> None:
        self.llm = llm or StubLLM(prefix="[relance]")
        self.sender_name = sender_name

    def propose(self, context: dict[str, Any]) -> Action:
        n = context.get("count", "?")
        return Action(type=ActionType.ANALYZE, description=f"Rédiger {n} relance(s) de facture",
                      actor=self.name)

    def draft_reminders(
        self,
        governance: GovernanceService,
        invoices: list[Invoice],
        granted: AutonomyLevel = AutonomyLevel.A1,
        memory: MemoryStore | None = None,
    ) -> tuple[Any, list[Reminder]]:
        """Rédige une relance par facture (A1). N'envoie rien : produit des brouillons."""
        with span("invoice.draft", **{"helyos.count": len(invoices)}):
            verdict = governance.submit(self.propose({"count": len(invoices)}), granted)
            if verdict.decision is not Decision.ALLOW:
                return verdict, []

            reminders: list[Reminder] = []
            for inv in invoices:
                tone = _tone_for(inv.days_late)
                prompt = (
                    f"Rédige un e-mail de relance de facture impayée, en français, {_TONE_BRIEF[tone]}. "
                    f"Client : {inv.client}. Montant dû : {inv.amount_eur:.2f} €. "
                    f"Retard : {inv.days_late} jours. Référence : {inv.ref or 'N/A'}. "
                    f"Signé : {self.sender_name}. Court, poli, clair, avec un appel à régler."
                )
                body = self.llm.complete(prompt)
                subject = {
                    "courtois": f"Petit rappel — facture {inv.ref}",
                    "ferme": f"Relance — facture {inv.ref} en retard de {inv.days_late} j",
                    "dernier_rappel": f"Dernier rappel — facture {inv.ref}",
                }[tone]
                reminders.append(Reminder(ref=inv.ref, client=inv.client, email=inv.email,
                                          tone=tone, subject=subject, body=body))

            if memory is not None:
                memory.remember("dernieres_relances",
                                [r.__dict__ for r in reminders], namespace="factures")
            governance.bus.emit("invoice.drafted", count=len(reminders))
            return verdict, reminders

    def propose_send(
        self,
        governance: GovernanceService,
        reminder: Reminder,
        granted: AutonomyLevel = AutonomyLevel.A5,
        validated: bool = False,
    ) -> Any:
        """Proposer d'ENVOYER une relance. Action externe sensible → GR-2 : validation obligatoire."""
        with span("invoice.send", **{"helyos.ref": reminder.ref}):
            action = Action(
                type=ActionType.EXTERNAL_SENSITIVE,
                description=f"Envoyer la relance {reminder.ref} à {reminder.client} <{reminder.email}>",
                actor=self.name, sensitive=True, validated=validated,
            )
            return governance.submit(action, granted)
