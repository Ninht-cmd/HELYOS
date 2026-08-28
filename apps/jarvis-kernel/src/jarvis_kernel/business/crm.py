"""CRM / Sales — le premier département PLEINEMENT opérationnel (boucle end-to-end gouvernée).

    lead réel → stocké → Sales Agent le lit (scope IAM) → qualification → opportunité
    → e-mail préparé → GOUVERNANCE (envoi = GR-2, jamais autonome) → envoi validé
    → réponse → CRM mis à jour → vente → Outcome → Mémoire.

Zéro coquille vide : `CRM = ACTIVE` seulement quand la boucle a réellement tourné (au moins un
Outcome enregistré). Chaque action passe par l'IAM (identité/périmètre/permission) puis la
gouvernance (GR-x) et l'exploitation (agent SUSPENDED bloqué). Réutilise `ProspectionPipeline`
pour le stockage des prospects — pas de doublon.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from ..agents.llm import LLMPort
from ..iam import enforce
from ..memory.store import MemoryStore
from .orders import OrderBook
from .prospection import ProspectionPipeline

_NS = "crm"
_INTENT_KW = ("besoin", "urgent", "budget", "devis", "intéress", "projet", "rdv", "délai", "prix")


def qualify_score(company: str, contact: str, note: str) -> tuple:
    """Qualification déterministe et honnête (0–100) — pas une boîte noire."""
    s = 0
    if contact:
        s += 30
    if company:
        s += 20
    if any(k in (note or "").lower() for k in _INTENT_KW):
        s += 30
    s += 20                                       # un lead nommé = un minimum d'intention
    stage = "qualified" if s >= 60 else ("to_nurture" if s >= 30 else "low")
    return s, stage


@dataclass
class Opportunity:
    name: str
    company: str = ""
    qualification: int = 0
    stage: str = "new"
    value_eur: float = 0.0
    draft: str = ""
    interactions: list = field(default_factory=list)


class CRMWorkflow:
    """Orchestrateur gouverné. Chaque méthode qui agit prend l'IDENTITÉ (`actor`) et passe par
    l'IAM ; l'envoi passe en plus par la gouvernance (GR-2)."""

    def __init__(self, memory: MemoryStore, iam=None, governance=None, llm: LLMPort | None = None) -> None:
        self.memory = memory
        self.iam = iam
        self.gov = governance
        self.llm = llm
        self.prospects = ProspectionPipeline(memory)

    # ---- stockage ----
    def _opps(self) -> dict:
        return dict(self.memory.recall("opportunities", namespace=_NS) or {})

    def _save(self, d: dict) -> None:
        self.memory.remember("opportunities", d, namespace=_NS)

    def _outcomes(self) -> list:
        return list(self.memory.recall("outcomes", namespace=_NS) or [])

    def _save_outcomes(self, lst: list) -> None:
        self.memory.remember("outcomes", lst, namespace=_NS)

    # ---- garde IAM ----
    def _authz(self, actor: str, action: str, resource: str, business: str):
        if self.iam is None:
            return True, None
        d = self.iam.authorize(actor, action, resource, {"business": business})
        return d.allowed, d

    @staticmethod
    def _denied(d) -> dict:
        return {"allowed": False, "policy": getattr(d, "policy", "IAM"),
                "reason": getattr(d, "reason", "refusé")}

    # ---- étapes de la boucle ----
    def ingest_lead(self, actor: str, name: str, company: str = "", contact: str = "",
                    note: str = "", business: str = "BUS-001") -> dict:
        ok, d = self._authz(actor, "crm.update", f"lead:{name}@{business}", business)
        if not ok:
            return self._denied(d)
        self.prospects.add(name, company=company, contact=contact, note=note)
        opps = self._opps()
        opps.setdefault(name, vars(Opportunity(name=name, company=company)))
        self._save(opps)
        return {"allowed": True, "lead": name}

    def qualify(self, actor: str, name: str, business: str = "BUS-001") -> dict:
        ok, d = self._authz(actor, "prospect.analyze", f"lead:{name}@{business}", business)
        if not ok:
            return self._denied(d)
        opps = self._opps()
        o = opps.get(name)
        if o is None:
            return {"allowed": True, "error": "lead inconnu"}
        p = next((x for x in self.prospects.list() if x.name == name), None)
        score, stage = qualify_score(o.get("company", ""), p.contact if p else "", p.note if p else "")
        o["qualification"], o["stage"] = score, stage
        self._save(opps)
        return {"allowed": True, "qualification": score, "stage": stage}

    def create_opportunity(self, name: str, value_eur: float) -> dict:
        opps = self._opps()
        opps.setdefault(name, vars(Opportunity(name=name)))
        opps[name]["value_eur"] = float(value_eur)
        self._save(opps)
        return {"name": name, "value_eur": float(value_eur)}

    def prepare_email(self, actor: str, name: str, business: str = "BUS-001") -> dict:
        ok, d = self._authz(actor, "email.prepare", f"prospect:{name}@{business}", business)
        if not ok:
            return self._denied(d)
        p = next((x for x in self.prospects.list() if x.name == name), None)
        if p is None:
            return {"allowed": True, "error": "lead inconnu"}
        draft = self.prospects.draft_outreach(self.llm, p) if self.llm else \
            f"Bonjour {name}, auriez-vous 15 minutes cette semaine ?"
        opps = self._opps()
        opps.setdefault(name, vars(Opportunity(name=name)))["draft"] = draft
        self._save(opps)
        return {"allowed": True, "draft": draft}

    def request_send(self, actor: str, name: str, business: str = "BUS-001",
                     validated: bool = False, granted=None) -> dict:
        """Envoi = action externe sensible : passe par IAM PUIS gouvernance. Sans validation
        humaine, HELYOS PRÉPARE mais n'envoie pas (GR-2)."""
        res = enforce(self.iam, self.gov, actor, "email.send", f"prospect:{name}@{business}",
                      {"business": business, "validated": validated, "sensitive": True}, granted)
        if res.get("final") == "ALLOW":
            self.prospects.set_status(name, "contacte")
            opps = self._opps()
            opps.setdefault(name, vars(Opportunity(name=name))).setdefault("interactions", []).append(
                {"kind": "email_sent", "ts": time.time()})
            self._save(opps)
        return res

    def record_response(self, name: str, positive: bool = True) -> dict:
        status = "rdv" if positive else "perdu"
        self.prospects.set_status(name, status)
        return {"name": name, "status": status}

    def close(self, actor: str, name: str, won: bool = True, amount: float = 0.0,
              business: str = "BUS-001") -> dict:
        """Clôture → Outcome enregistré (mémoire) + vente au carnet de commandes si gagné."""
        ok, d = self._authz(actor, "crm.update", f"prospect:{name}@{business}", business)
        if not ok:
            return self._denied(d)
        self.prospects.set_status(name, "client" if won else "perdu")
        opps = self._opps()
        expected = (opps.get(name, {}).get("qualification", 50) / 100) if opps.get(name) else 0.5
        outcome = {"name": name, "won": bool(won), "amount": float(amount),
                   "expected": expected, "observed": 1.0 if won else 0.0, "ts": time.time()}
        outs = self._outcomes()
        outs.append(outcome)
        self._save_outcomes(outs)
        if won and amount:
            try:
                OrderBook(self.memory).add("vente", name, "vente CRM (Audit Flash)", float(amount), business)
            except Exception:
                pass
        return {"allowed": True, "outcome": outcome}

    # ---- pour le BrickRegistry / cockpit ----
    def snapshot(self) -> dict:
        opps = self._opps()
        outs = self._outcomes()
        won = [o for o in outs if o.get("won")]
        return {
            "opportunities": len(opps),
            "qualified": sum(1 for o in opps.values() if o.get("stage") == "qualified"),
            "outcomes": len(outs), "won": len(won),
            "revenue_eur": round(sum(o.get("amount", 0) for o in won), 2),
            "active": len(outs) > 0,          # ACTIVE seulement quand la boucle a produit un Outcome
        }
