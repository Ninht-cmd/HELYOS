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
    kind: str            # analyze | compare | simulate | propose | execute | reuse
    domain: str          # supply_chain | finance | general | dev
    side_effect: bool = False    # étape à effet externe -> gouvernance
    lever: bool = False          # nouveau levier (recherché après un succès partiel)


@dataclass
class Capability:
    name: str
    domains: set
    handler: object      # (SubGoal, dict) -> {result, confidence, sources}


class Planner:
    """Décompose un objectif en sous-objectifs (méthodes HTN-lite)."""

    def decompose(self, objective: str, insights: list | None = None) -> list[SubGoal]:
        o = (objective or "").lower()
        if re.search(r"projet|d[ée]p[oô]t|repo|code|bug|corrig|analyse.{0,15}helyos|github", o):
            return [
                SubGoal("Lire l'état réel du dépôt (commits, fichiers modifiés)", "read", "dev"),
                SubGoal("Identifier un problème dans le projet (TODO/FIXME)", "analyze", "dev"),
                SubGoal("Préparer un correctif et demander l'autorisation avant l'action sensible",
                        "propose", "dev", True),
            ]
        if re.search(r"co[uû]t|d[ée]pense|r[ée]duire|[ée]conom", o):
            # Si un LEVIER précédent a partiellement réussi : conserver le gain confirmé et
            # chercher d'AUTRES leviers plutôt que répéter la même décision.
            if insights and any(i.reusable for i in insights):
                return [
                    SubGoal("Conserver le gain confirmé (décision précédente déjà validée)", "reuse", "general"),
                    SubGoal("Analyser le coût de transport", "analyze", "general", lever=True),
                    SubGoal("Analyser la taille des commandes (EOQ)", "analyze", "general", lever=True),
                    SubGoal("Analyser les stocks de sécurité", "analyze", "general", lever=True),
                    SubGoal("Simuler la combinaison des nouveaux leviers", "simulate", "general", lever=True),
                    SubGoal("Proposer le meilleur nouveau plan (hors décision déjà prise)", "propose", "general", True),
                ]
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
            granted: AutonomyLevel = AutonomyLevel.A2, memory=None) -> dict:
        from .outcome import OutcomeAnalyzer
        # 1. INTERROGER LA MÉMOIRE avant de planifier : refus passés + RÉSULTATS mesurés.
        recall = memory.retrieve(objective) if memory is not None else {}
        insights = OutcomeAnalyzer().insights(memory, objective) if memory is not None else []
        memory_context = OutcomeAnalyzer().render(memory, insights) if memory is not None else ""
        objective_id = memory.start_episode(objective) if memory is not None else None
        ctx = {**(context or {}), "memory_recall": recall, "insights": insights,
               "objective_id": objective_id, "memory": memory}

        subgoals = self.planner.decompose(objective, insights)
        reuses_confirmed_gain = any(sg.kind == "reuse" for sg in subgoals)
        nouveaux_leviers = sum(1 for sg in subgoals if sg.lever)
        decisions_proposees = []

        steps = []
        for i, sg in enumerate(subgoals, 1):
            cap = self.route(sg)
            out = (cap.handler(sg, ctx) if cap
                   else {"result": f"(aucun agent pour « {sg.domain} »)", "confidence": 0.2, "sources": []})
            gov = None
            if sg.side_effect and governance is not None:
                v = governance.submit(Action(type=ActionType.EXTERNAL_SENSITIVE, actor="orchestrator",
                                             description=sg.text, sensitive=True), granted)
                gov = {"decision": v.decision.value, "rule": v.rule, "reason": v.reason}
            step = {"n": i, "sous_objectif": sg.text, "kind": sg.kind, "domaine": sg.domain,
                    "agent": cap.name if cap else None, "resultat": out["result"],
                    "confiance": round(out.get("confidence", 0.5), 2),
                    "sources": out.get("sources", []), "gouvernance": gov, "decision_id": None}
            # 2. ENREGISTRER dans la mémoire (événement ; et décision si l'agent en propose une)
            if memory is not None:
                memory.record_event(sg.kind, objective_id, step["agent"] or "?", out["result"],
                                    status="inferred", confidence=step["confiance"],
                                    sources=step["sources"], governance=gov or {},
                                    entities=out.get("decision", {}).get("entities", []))
                dec = out.get("decision")
                if dec is not None:
                    step["decision_id"] = memory.record_decision(
                        objective_id, step["agent"] or "?", dec["content"], status="proposed",
                        confidence=step["confiance"], sources=step["sources"], governance=gov or {},
                        entities=dec.get("entities", []))
            if out.get("decision"):
                decisions_proposees.append(out["decision"]["content"])
            steps.append(step)

        conf = round(sum(s["confiance"] for s in steps) / len(steps), 2) if steps else 0.0
        awaiting = any(s["gouvernance"] and s["gouvernance"]["decision"] == "require_validation" for s in steps)
        return {"objectif": objective, "objective_id": objective_id, "etapes": steps,
                "confiance_globale": conf, "en_attente_validation": awaiting, "memoire": recall,
                "memory_context": memory_context, "insights": insights,
                "reuses_confirmed_gain": reuses_confirmed_gain, "nouveaux_leviers": nouveaux_leviers,
                "decisions_proposees": decisions_proposees}


# ---------------------------------------------------------------- agents réels enregistrés
def _supply_chain_handler(sg: SubGoal, ctx: dict) -> dict:
    """Vrais comportements DIFFÉRENTS selon le sous-objectif (analyze / compare / simulate)."""
    rows = ctx.get("rows")
    if not rows:
        return {"result": "supply chain : aucune donnée de réceptions fournie.", "confidence": 0.3, "sources": []}
    from .domains.supply_chain import inventory_policy
    from .domains.supply_chain_agent import learn_suppliers
    prior = ctx.get("prior_lead_time", 9.0)
    sup = learn_suppliers(rows, prior)
    target = ctx.get("target", next(iter(sup)))
    t = sup.get(target, {"learned": 0.0, "n": 0})
    conf = min(0.95, 0.55 + 0.015 * t["n"])
    srcs = ["data/receptions.csv", "Learning Loop"]
    decision = None

    if sg.kind == "analyze":                          # diagnostiquer la dérive
        drift = round(t["learned"] - prior, 2)
        res = (f"Diagnostic : {target} délai réel {t['learned']} j sur {t['n']} réceptions "
               f"(dérive {drift:+} j vs {prior} j de référence).")
    elif sg.kind == "compare":                        # classer les fournisseurs -> DÉCISION
        ranked = sorted(sup.items(), key=lambda kv: kv[1]["learned"])
        best = ranked[0][0]
        res = ("Comparaison délais : " + " ; ".join(f"{s} {v['learned']} j" for s, v in ranked)
               + f". Recommandé : {best} (le plus rapide).")
        decision = {"content": f"Passage vers {best}", "entities": [f"supplier:{best}"]}
    elif sg.kind == "simulate":                       # chiffrer l'impact de la dérive
        pp = ctx.get("policy_params")
        if pp:
            p0 = inventory_policy(**{**pp, "lead_time": prior})
            p1 = inventory_policy(**{**pp, "lead_time": t["learned"]})
            res = (f"Simulation ({prior}→{t['learned']} j) : point de commande "
                   f"{p0['reorder_point']}→{p1['reorder_point']} u, coût "
                   f"{p0['total_cost']}→{p1['total_cost']} €/an.")
        else:
            res = f"Simulation de l'impact du délai {t['learned']} j (paramètres de politique manquants)."
        conf = min(conf, 0.85)
    else:
        res = f"{len(sup)} fournisseur(s) analysé(s) sur données réelles."
    out = {"result": res, "confidence": conf, "sources": srcs}
    if decision is not None:
        out["decision"] = decision
    return out


def _dev_findings(ctx: dict) -> list[dict]:
    """Findings AST normalisés (avec preuve), calculés une fois et mis en cache dans ctx."""
    if "_findings" in ctx:
        return ctx["_findings"]
    bus = ctx.get("bus")
    fs = (bus.read("project", "findings", limit=20).data if bus is not None else []) or []
    ctx["_findings"] = fs
    return fs


def _dev_candidates(ctx: dict) -> list[str]:
    """Recommandations AST, RANGÉES par fiabilité mesurée de l'analyseur : un analyseur
    devenu peu fiable (ex. TestCoverageMapper à 0.034 après vérification runtime) coule au
    fond et ne fait plus remonter seul une priorité. Injectables via ctx['candidates']."""
    if ctx.get("candidates"):
        return list(ctx["candidates"])
    findings = _dev_findings(ctx)
    mem = ctx.get("memory")
    if mem is not None:
        from .confidence import analyzer_reliability
        order = {"high": 0, "medium": 1, "low": 2}
        rel = {c: analyzer_reliability(mem, c)[0]
               for c in {f["category"] for f in findings}}
        findings = sorted(findings, key=lambda f: (-rel.get(f["category"], 0.6),
                                                   order.get(f["severity"], 3)))
        ctx["_findings"] = findings                # le cache reflète le nouvel ordre
    return [f["recommendation"] for f in findings] or ["amélioration générique"]


def _dev_handler(sg: SubGoal, ctx: dict) -> dict:
    """Agent développement : lit le dépôt DISTANT (GitHub), analyse le code, ÉVITE ce qui
    a déjà été refusé (mémoire), et propose sous validation."""
    bus = ctx.get("bus")
    recall = ctx.get("memory_recall", {}) or {}
    rejected = {r["content"] for r in recall.get("rejected", [])}

    if sg.kind == "read":
        if bus is None:
            return {"result": "dev : aucun tool bus.", "confidence": 0.2, "sources": []}
        gh = bus.read("github", "repo")
        ghc = bus.read("github", "commits", n=3)
        if gh.ok:
            d = gh.data
            res = (f"Dépôt DISTANT lu (GitHub API) : {d['full_name']} · {d['language']} · "
                   f"{d['stars']}★ · {d['open_issues']} issue(s) ouverte(s) · poussé "
                   f"{str(d['pushed_at'])[:10]} · {len(ghc.data or [])} commits récents.")
            return {"result": res, "confidence": 0.9, "sources": ["GitHub API (distant)"]}
        commits = bus.read("project", "commits", n=3)
        mods = bus.read("project", "modules")
        return {"result": f"(GitHub indisponible) dépôt local : {len(commits.data or [])} commits, "
                f"{mods.data} modules.", "confidence": 0.6, "sources": ["git local"]}

    findings = _dev_findings(ctx)
    cands = _dev_candidates(ctx)
    fresh = [c for c in cands if c not in rejected]

    if sg.kind == "analyze":
        note = " (j'écarte une piste déjà refusée)" if len(fresh) != len(cands) else ""
        top = next((f for f in findings if f["recommendation"] in fresh),
                   findings[0] if findings else None)
        if top:
            res = (f"{len(findings)} findings AST{note} ; priorité "
                   f"[{top['category']}/{top['severity']}] {top['symbol']} — {top['recommendation']} "
                   f"(preuve : {top['evidence'][0]}).")
            return {"result": res, "confidence": top["confidence"],
                    "sources": ["analyse AST : imports · code mort · complexité · tests"]}
        return {"result": "aucun finding AST.", "confidence": 0.5, "sources": ["analyse AST"]}

    if sg.kind == "propose":
        chosen = fresh[0] if fresh else (cands[0] if cands else "amélioration générique")
        top = next((f for f in findings if f["recommendation"] == chosen), None)
        pre = ""
        if rejected:
            y = next(iter(rejected))
            pre = f"La piste « {y} » avait été refusée ; je ne la re-propose pas. "
        if top:
            from .confidence import composite_for
            cc = composite_for(top, ctx.get("memory"))
            res = (pre + f"Je propose : {chosen} [{top['category']}/{top['severity']}]. "
                   f"Preuve : {', '.join(top['evidence'][:2])}. Confiance {cc.explain()}. "
                   f"Patch préparé, en attente de ton autorisation.")
            return {"result": res, "confidence": cc.balanced, "sources": ["analyse AST + GitHub"],
                    "composite": cc.explain(),
                    "decision": {"content": chosen, "entities": [top["symbol"], f"category:{top['category']}"]}}
        res = pre + f"Je propose : {chosen} — patch préparé, en attente de ton autorisation."
        return {"result": res, "confidence": 0.6, "sources": ["analyse AST"],
                "decision": {"content": chosen, "entities": ["repo"]}}

    return {"result": sg.text, "confidence": 0.5, "sources": []}


def _finance_handler(sg: SubGoal, ctx: dict) -> dict:
    cost, pct = ctx.get("annual_cost"), ctx.get("target_reduction_pct")
    if cost and pct:
        save = cost * pct / 100.0
        return {"result": f"Coût annuel {cost:.0f} € ; cible −{pct}% ⇒ {save:.0f} € à retrancher.",
                "confidence": 0.9, "sources": ["Domaine Finance"]}
    return {"result": "Structure de coûts analysée (données partielles).", "confidence": 0.4,
            "sources": ["Domaine Finance"]}


def _general_handler(sg: SubGoal, ctx: dict) -> dict:
    if sg.kind == "reuse":
        return {"result": "Gain confirmé conservé — je réutilise la décision précédente au lieu de la répéter.",
                "confidence": 0.8, "sources": ["mémoire"]}
    return {"result": f"{sg.text} — préparé, prêt pour validation." if sg.side_effect
            else f"{sg.text} — traité.", "confidence": 0.55, "sources": []}


def default_orchestrator() -> Orchestrator:
    o = Orchestrator()
    o.register(Capability("supply_chain_agent", {"supply_chain"}, _supply_chain_handler))
    o.register(Capability("finance_agent", {"finance"}, _finance_handler))
    o.register(Capability("dev_agent", {"dev"}, _dev_handler))
    o.register(Capability("general_advisor", {"general"}, _general_handler))
    return o
