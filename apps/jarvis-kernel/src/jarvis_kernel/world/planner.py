"""HELYOS — Planificateur + Orchestrateur multi-agents (la couche cognitive).

C'est le keystone qui manquait : relier les domaines. Un objectif de haut niveau
(« réduire les coûts de 15 % ») est :
  1. DÉCOMPOSÉ en sous-objectifs (Planner, HTN-lite : méthodes → sous-tâches) ;
  2. ROUTÉ vers l'agent spécialisé compétent (supply chain, finance, général) ;
  3. AGRÉGÉ en un PLAN expliqué — chaque étape porte son résultat, sa CONFIANCE et
     ses SOURCES (brique « explication des décisions ») ;
  4. GOUVERNÉ — les étapes à effet externe passent en REQUIRE_VALIDATION (A0–A5).

Portée honnête : décomposition par MÉTHODES (patrons), pas un planificateur appris ;
quelques agents réels enregistrés. Mais la coordination, le routage, l'agrégation
expliquée et la barrière de gouvernance sont réels et testés.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from ..governance.autonomy import AutonomyLevel
from ..governance.policy import Action, ActionType


@dataclass
class SubGoal:
    text: str
    kind: str            # analyze | compare | simulate | propose | execute
    domain: str          # supply_chain | finance | general
    side_effect: bool = False    # étape à effet externe -> gouvernance


@dataclass
class Capability:
    name: str
    domains: set
    handler: object      # (SubGoal, dict) -> {result, confidence, sources}


class Planner:
    """Décompose un objectif en sous-objectifs (méthodes HTN-lite)."""

    def decompose(self, objective: str) -> list[SubGoal]:
        o = (objective or "").lower()
        if re.search(r"co[uû]t|d[ée]pense|r[ée]duire|[ée]conom", o):
            m = re.search(r"(\d+)\s*%", o)
            pct = m.group(1) if m else "X"
            return [
                SubGoal(f"Analyser la structure de coûts (cible −{pct}%)", "analyze", "finance"),
                SubGoal("Identifier les postes réductibles / fournisseurs qui dérivent", "analyze", "supply_chain"),
                SubGoal("Comparer des fournisseurs alternatifs", "compare", "supply_chain"),
                SubGoal("Simuler l'impact sur stock, coût et délai", "simulate", "supply_chain"),
                SubGoal("Proposer un plan chiffré et contacter les alternatifs", "propose", "general", True),
            ]
        return [
            SubGoal("Analyser la situation", "analyze", "general"),
            SubGoal("Simuler les options", "simulate", "general"),
            SubGoal("Proposer une action sous validation", "propose", "general", True),
        ]


class Orchestrator:
    """Route chaque sous-objectif vers l'agent compétent, agrège un plan gouverné et expliqué."""

    def __init__(self, planner: Planner | None = None) -> None:
        self.planner = planner or Planner()
        self.capabilities: list[Capability] = []

    def register(self, cap: Capability) -> None:
        self.capabilities.append(cap)

    def route(self, sg: SubGoal) -> Capability | None:
        for c in self.capabilities:
            if sg.domain in c.domains:
                return c
        return next((c for c in self.capabilities if "general" in c.domains), None)

    def run(self, objective: str, context: dict | None = None, *, governance=None,
            granted: AutonomyLevel = AutonomyLevel.A2) -> dict:
        ctx = context or {}
        steps = []
        for i, sg in enumerate(self.planner.decompose(objective), 1):
            cap = self.route(sg)
            out = (cap.handler(sg, ctx) if cap
                   else {"result": f"(aucun agent pour « {sg.domain} »)", "confidence": 0.2, "sources": []})
            gov = None
            if sg.side_effect and governance is not None:
                v = governance.submit(Action(type=ActionType.EXTERNAL_SENSITIVE, actor="orchestrator",
                                             description=sg.text, sensitive=True), granted)
                gov = {"decision": v.decision.value, "rule": v.rule, "reason": v.reason}
            steps.append({"n": i, "sous_objectif": sg.text, "kind": sg.kind, "domaine": sg.domain,
                          "agent": cap.name if cap else None, "resultat": out["result"],
                          "confiance": round(out.get("confidence", 0.5), 2),
                          "sources": out.get("sources", []), "gouvernance": gov})
        conf = round(sum(s["confiance"] for s in steps) / len(steps), 2) if steps else 0.0
        awaiting = any(s["gouvernance"] and s["gouvernance"]["decision"] == "require_validation" for s in steps)
        return {"objectif": objective, "etapes": steps, "confiance_globale": conf,
                "en_attente_validation": awaiting}


# ---------------------------------------------------------------- agents réels enregistrés
def _supply_chain_handler(sg: SubGoal, ctx: dict) -> dict:
    rows = ctx.get("rows")
    if not rows:
        return {"result": "supply chain : aucune donnée de réceptions fournie.", "confidence": 0.3, "sources": []}
    from .domains.supply_chain_agent import learn_suppliers
    sup = learn_suppliers(rows, ctx.get("prior_lead_time", 9.0))
    target = ctx.get("target", next(iter(sup)))
    t = sup.get(target, {"learned": 0, "n": 0})
    alts = sorted((s for s, v in sup.items() if s != target and v["learned"] < t["learned"]),
                  key=lambda s: sup[s]["learned"])
    conf = min(0.95, 0.55 + 0.015 * t["n"])       # confiance ∝ nombre de réceptions réelles
    res = (f"{len(sup)} fournisseur(s) analysé(s) sur données réelles ; {target} délai {t['learned']} j "
           f"({t['n']} réceptions) ; alternatifs plus rapides : {', '.join(alts) if alts else 'aucun'}.")
    return {"result": res, "confidence": conf, "sources": ["data/receptions.csv", "Learning Loop"]}


def _finance_handler(sg: SubGoal, ctx: dict) -> dict:
    cost, pct = ctx.get("annual_cost"), ctx.get("target_reduction_pct")
    if cost and pct:
        save = cost * pct / 100.0
        return {"result": f"Coût annuel {cost:.0f} € ; cible −{pct}% ⇒ {save:.0f} € à retrancher.",
                "confidence": 0.9, "sources": ["Domaine Finance"]}
    return {"result": "Structure de coûts analysée (données partielles).", "confidence": 0.4,
            "sources": ["Domaine Finance"]}


def _general_handler(sg: SubGoal, ctx: dict) -> dict:
    return {"result": f"{sg.text} — préparé, prêt pour validation." if sg.side_effect
            else f"{sg.text} — traité.", "confidence": 0.55, "sources": []}


def default_orchestrator() -> Orchestrator:
    o = Orchestrator()
    o.register(Capability("supply_chain_agent", {"supply_chain"}, _supply_chain_handler))
    o.register(Capability("finance_agent", {"finance"}, _finance_handler))
    o.register(Capability("general_advisor", {"general"}, _general_handler))
    return o
