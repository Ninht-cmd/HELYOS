"""Prospection — le poste de travail quotidien du Plan Cash (RFC-0008).

C'est ici qu'HELYOS devient un OUTIL DE TRAVAIL et pas une démo : tu ajoutes tes
prospects, il sait qui relancer (J+3 puis J+7, le rythme du Plan), il rédige les
messages (toi tu valides et envoies — GR-2), et le Pouls te rappelle les relances
dues dans le briefing. Les trois chiffres du vendredi sortent de `stats()`.

Honnêteté : ce module ne trouve PAS de prospects tout seul (pas de scraping) et
n'envoie RIEN sans toi. Il organise TON travail de vente — c'est déjà ce qui
manque le plus.
"""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field

from ..agents.llm import LLMPort
from ..memory.store import MemoryStore

STATUTS = ("a_contacter", "contacte", "relance_1", "relance_2",
           "repondu", "rdv", "client", "perdu")
# le rythme du Plan Cash : 1re relance à J+3, 2e à J+7 (soit +4 après la 1re)
FOLLOWUP_AFTER_S = {"contacte": 3 * 86400, "relance_1": 4 * 86400}
_NS = "prospection"


@dataclass
class Prospect:
    name: str
    company: str = ""
    contact: str = ""            # e-mail / téléphone / LinkedIn — au choix
    note: str = ""
    status: str = "a_contacter"
    ts_last: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return asdict(self)


class ProspectionPipeline:
    """Pipeline mémoire-adossé (même pattern que le portefeuille)."""

    def __init__(self, memory: MemoryStore) -> None:
        self.memory = memory

    def _all(self) -> dict[str, dict]:
        return dict(self.memory.recall("prospects", namespace=_NS) or {})

    def _save(self, data: dict[str, dict]) -> None:
        self.memory.remember("prospects", data, namespace=_NS)

    def add(self, name: str, company: str = "", contact: str = "",
            note: str = "") -> Prospect:
        data = self._all()
        if name in data:                      # idempotent : pas de doublon silencieux
            return Prospect(**data[name])
        p = Prospect(name=name, company=company, contact=contact, note=note)
        data[name] = p.to_dict()
        self._save(data)
        return p

    def set_status(self, name: str, status: str) -> Prospect:
        if status not in STATUTS:
            raise ValueError(f"statut inconnu : {status!r} (valides : {', '.join(STATUTS)})")
        data = self._all()
        if name not in data:
            raise KeyError(f"prospect inconnu : {name!r}")
        data[name]["status"] = status
        data[name]["ts_last"] = time.time()
        self._save(data)
        return Prospect(**data[name])

    def list(self) -> list[Prospect]:
        return [Prospect(**d) for d in self._all().values()]

    def due_followups(self, now: float | None = None) -> list[tuple[Prospect, str]]:
        """Qui relancer MAINTENANT, et vers quel statut (relance_1 ou relance_2)."""
        now = now or time.time()
        due = []
        for p in self.list():
            wait = FOLLOWUP_AFTER_S.get(p.status)
            if wait is not None and now - p.ts_last >= wait:
                due.append((p, "relance_1" if p.status == "contacte" else "relance_2"))
        return due

    def stats(self) -> dict:
        """Les chiffres du vendredi — comptés, jamais embellis."""
        by = {s: 0 for s in STATUTS}
        for p in self.list():
            by[p.status] = by.get(p.status, 0) + 1
        contacted = sum(v for s, v in by.items() if s != "a_contacter")
        return {"total": sum(by.values()), "contactes": contacted,
                "reponses": by["repondu"] + by["rdv"] + by["client"],
                "clients": by["client"], "a_relancer": len(self.due_followups()),
                "par_statut": {s: v for s, v in by.items() if v}}

    def draft_outreach(self, llm: LLMPort, p: Prospect,
                       offer: str = "automatisation administrative (Audit Flash 490 €)",
                       ) -> str:
        """Rédige un message court et personnalisé. RIEN n'est envoyé : GR-2."""
        prompt = (f"Rédige un e-mail de prospection FRANÇAIS de 4 phrases maximum, direct et "
                  f"sans jargon, pour {p.name}" + (f" ({p.company})" if p.company else "") +
                  f". Offre : {offer}. Terminer par une question fermée proposant 15 minutes "
                  f"d'échange. Pas de flatterie, pas de promesse de résultat.")
        try:
            draft = llm.complete(prompt).strip()
        except Exception:
            draft = ""
        if not draft or "Rédige un e-mail" in draft:     # StubLLM / hors ligne : gabarit honnête
            draft = (f"Bonjour {p.name},\n\nJ'aide les artisans et petites entreprises à "
                     f"supprimer ~10 h de travail administratif par mois ({offer}). "
                     f"Le premier diagnostic est livré en 72 h. "
                     f"Auriez-vous 15 minutes cette semaine pour voir si ça s'applique "
                     f"à {p.company or 'votre activité'} ?")
        return draft
