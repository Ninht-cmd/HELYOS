"""Livre de caisse — la colonne vertébrale financière du Dossier Business (RFC-0014).

Chaque euro qui ENTRE ou SORT d'un business est une écriture horodatée, immuable,
par business. Le « CA » affiché partout (board, briefing, portefeuille) cesse d'être
une métrique posée à la main : il devient LA SOMME DES ÉCRITURES — vérifiable.

Honnêteté et périmètre, sans ambiguïté :
- C'est une comptabilité de CAISSE de pilotage, PAS une comptabilité légale
  (pas de TVA, pas d'amortissements, pas de grand livre). Ton expert-comptable
  reste obligatoire ; ce livre lui simplifie la vie, il ne le remplace pas.
- ENREGISTRER un paiement déjà reçu/effectué = bookkeeping interne (A1).
  EFFECTUER un paiement reste GR-7 : jamais autonome. Ce module écrit l'histoire,
  il ne touche pas l'argent.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import asdict, dataclass, field

from ..memory.store import MemoryStore
from .portfolio import BusinessPortfolio

_NS = "ledger"
KINDS = ("recette", "depense")


@dataclass(frozen=True)
class Entry:
    business: str
    kind: str                 # recette | depense
    amount_eur: float
    label: str
    ts: float = field(default_factory=time.time)
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:10])

    def to_dict(self) -> dict:
        return asdict(self)


class Ledger:
    """Écritures append-only par business, adossées au MemoryStore."""

    def __init__(self, memory: MemoryStore, portfolio: BusinessPortfolio | None = None) -> None:
        self.memory = memory
        self.portfolio = portfolio

    def _entries_raw(self, business: str) -> list[dict]:
        return list(self.memory.recall(business, namespace=_NS) or [])

    def add(self, business: str, kind: str, amount_eur: float, label: str = "") -> Entry:
        if kind not in KINDS:
            raise ValueError(f"type d'écriture inconnu : {kind!r} (recette | depense)")
        amount_eur = round(float(amount_eur), 2)
        if amount_eur <= 0:
            raise ValueError("le montant doit être strictement positif")
        e = Entry(business=business, kind=kind, amount_eur=amount_eur, label=label)
        data = self._entries_raw(business)
        data.append(e.to_dict())
        self.memory.remember(business, data, namespace=_NS)
        self._sync_portfolio(business)
        return e

    def entries(self, business: str, limit: int = 50) -> list[Entry]:
        return [Entry(**d) for d in self._entries_raw(business)[-limit:]]

    def summary(self, business: str) -> dict:
        rec = dep = 0.0
        for d in self._entries_raw(business):
            if d["kind"] == "recette":
                rec += d["amount_eur"]
            else:
                dep += d["amount_eur"]
        return {"business": business, "recettes_eur": round(rec, 2),
                "depenses_eur": round(dep, 2), "solde_eur": round(rec - dep, 2),
                "ecritures": len(self._entries_raw(business))}

    def global_summary(self) -> dict:
        """La caisse de la holding : somme de tous les business qui ont des écritures."""
        businesses = ([b.name for b in self.portfolio.list()] if self.portfolio
                      else [i.key for i in self.memory.all(_NS)])
        per = [self.summary(n) for n in businesses]
        per = [s for s in per if s["ecritures"]]
        return {"recettes_eur": round(sum(s["recettes_eur"] for s in per), 2),
                "depenses_eur": round(sum(s["depenses_eur"] for s in per), 2),
                "solde_eur": round(sum(s["solde_eur"] for s in per), 2),
                "par_business": per}

    def _sync_portfolio(self, business: str) -> None:
        """Le CA affiché = la somme des écritures. Une seule source de vérité."""
        if self.portfolio is None or self.portfolio.get(business) is None:
            return
        s = self.summary(business)
        self.portfolio.set_metric(business, "revenue_eur", s["recettes_eur"])
        self.portfolio.set_metric(business, "depenses_eur", s["depenses_eur"])
        self.portfolio.set_metric(business, "solde_eur", s["solde_eur"])
