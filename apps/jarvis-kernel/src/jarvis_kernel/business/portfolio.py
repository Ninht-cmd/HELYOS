"""Portefeuille de business géré par HELYOS.

`BusinessPortfolio` = un registre persistant (via MemoryStore, namespace ``portfolio``)
de N business, chacun avec un état, des métriques et des tâches. C'est le « world model »
des business que HELYOS orchestre. La mise à jour du suivi (statut/métrique/tâche) est du
bookkeeping interne (aucun effet monde) ; les actions EXTERNES (publier, poster, déployer)
restent gouvernées par le PolicyEngine ailleurs.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from ..memory.store import MemoryStore

_NS = "portfolio"


@dataclass
class Business:
    name: str
    kind: str                 # 'ecommerce' | 'youtube' | 'opensource' | 'saas' | ...
    status: str = "idée"
    url: str = ""
    metrics: dict[str, Any] = field(default_factory=dict)   # ex. {"revenue_eur": 0}
    tasks: list[dict[str, Any]] = field(default_factory=list)  # {task, done, owner}

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(d: dict[str, Any]) -> "Business":
        return Business(**d)

    @property
    def open_tasks(self) -> int:
        return sum(1 for t in self.tasks if not t.get("done"))


class BusinessPortfolio:
    def __init__(self, memory: MemoryStore) -> None:
        self.memory = memory

    def register(self, b: Business) -> Business:
        self.memory.remember(b.name, b.to_dict(), namespace=_NS)
        return b

    def get(self, name: str) -> Business | None:
        d = self.memory.recall(name, namespace=_NS)
        return Business.from_dict(d) if d else None

    def list(self) -> list[Business]:
        return [Business.from_dict(i.value) for i in self.memory.all(_NS)]

    def set_status(self, name: str, status: str) -> Business | None:
        b = self.get(name)
        if b:
            b.status = status
            self.register(b)
        return b

    def set_metric(self, name: str, key: str, value: Any) -> Business | None:
        b = self.get(name)
        if b:
            b.metrics[key] = value
            self.register(b)
        return b

    def add_task(self, name: str, task: str, owner: str = "humain") -> Business | None:
        b = self.get(name)
        if b:
            b.tasks.append({"task": task, "done": False, "owner": owner})
            self.register(b)
        return b

    def complete_task(self, name: str, task_prefix: str) -> Business | None:
        b = self.get(name)
        if b:
            for t in b.tasks:
                if t["task"].startswith(task_prefix):
                    t["done"] = True
            self.register(b)
        return b

    def summary(self) -> list[dict[str, Any]]:
        return [{"name": b.name, "kind": b.kind, "status": b.status,
                 "metrics": b.metrics, "open_tasks": b.open_tasks} for b in self.list()]


def seed_known_businesses(portfolio: BusinessPortfolio) -> list[str]:
    """Amorce le portefeuille avec les business connus (idempotent — écrase). Le 4e est à confirmer."""
    known = [
        Business(name="Atelier Compagnon (boutique)", kind="ecommerce",
                 status="squelette prêt — bloqué sur Printful + paiement",
                 url="https://kgqc06-yq.myshopify.com",
                 metrics={"revenue_eur": 0, "produits": 5},
                 tasks=[{"task": "[HUMAIN] Connecter Printful (images+fabrication)", "done": False, "owner": "humain"},
                        {"task": "[HUMAIN] Activer le paiement (Stripe/Shopify Payments)", "done": False, "owner": "humain"},
                        {"task": "[GOUVERNÉ A2] Publier les produits", "done": False, "owner": "helyos"}]),
        Business(name="Chaîne YouTube faceless", kind="youtube",
                 status="scripts prêts — non lancée",
                 metrics={"abonnes": 0, "videos_publiees": 0, "objectif_seuil": 1000},
                 tasks=[{"task": "[HUMAIN] Publier 3-5 vidéos/semaine", "done": False, "owner": "humain"}]),
        Business(name="HELYOS open-source", kind="opensource",
                 status="public, en dev (Phase 3 faite)",
                 url="https://github.com/Ninht-cmd/HELYOS",
                 metrics={"stars": 0, "revenu_direct_eur": 0},
                 tasks=[{"task": "[HUMAIN] Build-in-public quotidien sur X", "done": False, "owner": "humain"}]),
        Business(name="HELYOS Services (automatisation admin)", kind="service",
                 status="v1 construit — agent 'relance de factures' opérationnel en démo",
                 metrics={"revenue_eur": 0, "clients": 0, "agents_v1": 1},
                 tasks=[{"task": "[HUMAIN] Valider la demande : montrer la démo à 3-5 artisans", "done": False, "owner": "humain"},
                        {"task": "[HELYOS] Brancher l'envoi SMTP derrière la gouvernance (A2)", "done": False, "owner": "helyos"},
                        {"task": "[HUMAIN] Décrocher le 1er client payant (niche étroite)", "done": False, "owner": "humain"}]),
    ]
    for b in known:
        portfolio.register(b)
    return [b.name for b in known]
