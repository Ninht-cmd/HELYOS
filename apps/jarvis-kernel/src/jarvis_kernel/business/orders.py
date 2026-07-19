"""Carnet de commandes — les deux sens du flux : ce qu'on VEND, ce qu'on ACHÈTE.

Le trou opérationnel qui restait : quand un client achète le pack, il faut suivre
la commande jusqu'à la livraison et l'encaissement ; et quand on commande à un
fournisseur (Printful, hébergeur…), il faut suivre l'achat jusqu'à réception.

- ``vente``  : commande reçue d'un CLIENT → à livrer → à encaisser.
- ``achat``  : commande passée à un FOURNISSEUR → à payer → à recevoir.

Contrat : ce module TRACE, il ne bouge pas d'argent. Marquer « payée » ne fait
qu'ouvrir une écriture de caisse SUGGÉRÉE ; l'encaissement réel reste une écriture
explicite (livre de caisse), et tout paiement sortant reste GR-7.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import asdict, dataclass, field

from ..memory.store import MemoryStore

_NS = "orders"
SENS = ("vente", "achat")
# cycles de vie : une vente se livre puis s'encaisse ; un achat se paie puis se reçoit
STATUTS_VENTE = ("recue", "en_preparation", "livree", "encaissee", "annulee")
STATUTS_ACHAT = ("a_passer", "commandee", "recue", "payee", "annulee")


@dataclass
class Order:
    sens: str                 # vente | achat
    partie: str               # le client (vente) ou le fournisseur (achat)
    objet: str                # produit / prestation
    montant_eur: float
    business: str = ""        # à quel business elle se rattache
    statut: str = ""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    ts: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return asdict(self)


class OrderBook:
    def __init__(self, memory: MemoryStore) -> None:
        self.memory = memory

    def _all(self) -> list[dict]:
        return list(self.memory.recall("carnet", namespace=_NS) or [])

    def _save(self, data: list[dict]) -> None:
        self.memory.remember("carnet", data, namespace=_NS)

    def add(self, sens: str, partie: str, objet: str, montant_eur: float,
            business: str = "") -> Order:
        if sens not in SENS:
            raise ValueError(f"sens inconnu : {sens!r} (vente | achat)")
        montant_eur = round(float(montant_eur), 2)
        if montant_eur < 0:
            raise ValueError("le montant ne peut pas être négatif")
        statut = "recue" if sens == "vente" else "a_passer"
        o = Order(sens=sens, partie=partie, objet=objet, montant_eur=montant_eur,
                  business=business, statut=statut)
        data = self._all()
        data.append(o.to_dict())
        self._save(data)
        return o

    def set_statut(self, order_id: str, statut: str) -> Order:
        data = self._all()
        for d in data:
            if d["id"] == order_id or d["id"].startswith(order_id):
                valid = STATUTS_VENTE if d["sens"] == "vente" else STATUTS_ACHAT
                if statut not in valid:
                    raise ValueError(f"statut invalide pour une {d['sens']} : {statut!r} "
                                     f"({', '.join(valid)})")
                d["statut"] = statut
                self._save(data)
                return Order(**d)
        raise KeyError(f"commande inconnue : {order_id!r}")

    def list(self, sens: str | None = None) -> list[Order]:
        return [Order(**d) for d in self._all() if sens is None or d["sens"] == sens]

    def to_deliver(self) -> list[Order]:
        """Ventes à livrer (reçues ou en préparation) — le travail client en attente."""
        return [o for o in self.list("vente") if o.statut in ("recue", "en_preparation")]

    def to_collect(self) -> list[Order]:
        """Ventes livrées mais pas encore encaissées — l'argent qui dort."""
        return [o for o in self.list("vente") if o.statut == "livree"]

    def to_pay(self) -> list[Order]:
        """Achats reçus mais pas payés (GR-7 : le paiement reste ta décision)."""
        return [o for o in self.list("achat") if o.statut == "recue"]

    def suppliers(self) -> list[str]:
        return sorted({o.partie for o in self.list("achat")})

    def summary(self) -> dict:
        ventes = self.list("vente")
        achats = self.list("achat")
        return {
            "ventes": len(ventes), "achats": len(achats),
            "a_livrer": len(self.to_deliver()),
            "a_encaisser": len(self.to_collect()),
            "a_encaisser_eur": round(sum(o.montant_eur for o in self.to_collect()), 2),
            "a_payer": len(self.to_pay()),
            "fournisseurs": self.suppliers(),
            "ca_livre_eur": round(sum(o.montant_eur for o in ventes
                                      if o.statut in ("livree", "encaissee")), 2),
        }
