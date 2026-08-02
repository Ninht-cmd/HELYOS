"""HELYOS Simulation Engine v1.3 — de « une trajectoire » à « une distribution de futurs ».

Jusqu'ici : action → trajectoire unique → choix. Le monde réel n'est pas ça. Ici :
action/plan → N futurs échantillonnés → distribution d'utilité → valeur espérée + RISQUE
→ décision. C'est le vrai franchissement H=1 → « 1000 futurs → trajectoire optimale ».

Cinq briques (toutes réelles, testées, chiffrées) :
  1. Monte-Carlo World Simulator : échantillonne les croyances (μ±σ) et re-dérive la chaîne.
  2. Stochastic Events           : un événement a une probabilité et un impact ; il tire.
  3. Risk Engine                 : E[U], σ, P(faillite), P(succès), CVaR, score ajusté au risque.
  4. Trajectory Ranking          : classe des PLANS (histoires) — avec garde-fou ressources (v1.2).
  5. Apprentissage causal (amorce): ``learn_elasticity`` — ajuste un coefficient causal par MCO.

Réutilise la colonne vertébrale probabiliste (croyances) + la Reality Layer (utilité, ressources).
Python pur ; ``random`` graine pour la reproductibilité.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from .ontology import KnowledgeGraph
from .reality import Response, company_utility, goal_attainment

_POS = {"money", "count", "metric", "months"}


@dataclass
class StochasticEvent:
    """Un événement incertain : se produit avec ``probability`` ; s'il tire, applique ses
    interventions (op ∈ mul|set|add) aux croyances visées."""
    name: str
    probability: float
    interventions: dict[str, float] = field(default_factory=dict)
    op: str = "mul"


@dataclass
class Plan:
    """Une HISTOIRE : une suite d'actions (effets) + les événements qui la menacent + le
    besoin agrégé en ressources (pour la faisabilité)."""
    name: str
    actions: list[Response] = field(default_factory=list)
    events: list[StochasticEvent] = field(default_factory=list)
    needs: dict = field(default_factory=dict)


# ---------------------------------------------------------------- échantillonnage
def _sample(graph: KnowledgeGraph, rng: random.Random) -> KnowledgeGraph:
    """Clone où chaque croyance de BASE est tirée de N(μ,σ) (bornée par nature), puis la
    chaîne dérivée est recalculée."""
    g = graph.clone()
    derived = {k for k, _, _ in g._derived}
    for key, b in g.world.beliefs.items():
        if key in derived or b.sigma <= 0:
            continue
        v = rng.gauss(b.value, b.sigma)
        if b.kind in _POS:
            v = max(0.0, v)
        elif b.kind == "ratio":
            v = min(1.0, max(0.0, v))
        b.value = v
    g.recompute()
    return g


def _apply_effects(g: KnowledgeGraph, effects) -> None:
    for key, op, amt in effects:
        b = g.world.get(key)
        if b is None:
            continue
        b.value = amt if op == "set" else (b.value + amt if op == "add" else b.value * amt)


def _pct(vals: list[float], p: float) -> float:
    if not vals:
        return 0.0
    s = sorted(vals)
    i = min(len(s) - 1, max(0, int(round(p / 100 * (len(s) - 1)))))
    return round(s[i], 4)


# ---------------------------------------------------------------- Monte-Carlo + Risk
def monte_carlo(graph: KnowledgeGraph, company_id: str, plan: Plan, now: float, *,
                n: int = 2000, seed: int = 0, bankrupt_attr: str = "cash",
                bankrupt_below: float = 0.0, goal_id: str | None = None) -> dict:
    """Tire N futurs pour un plan et agrège la distribution d'utilité + le risque."""
    rng = random.Random(seed)
    utils, bankrupts, successes = [], 0, 0
    for _ in range(n):
        g = _sample(graph, rng)
        for act in plan.actions:                      # 1) on DÉPLOIE le plan (capital engagé)…
            _apply_effects(g, act.effects)
        for ev in plan.events:                        # 2) …puis le monde frappe (événements)
            if rng.random() < ev.probability:
                _apply_effects(g, [(k, ev.op, v) for k, v in ev.interventions.items()])
        g.recompute()
        u, _ = company_utility(g, company_id, now)
        utils.append(u)
        if g.value(company_id, bankrupt_attr) < bankrupt_below:
            bankrupts += 1
        if goal_id and goal_attainment(g, goal_id, now) >= 1.0:
            successes += 1
    mean = sum(utils) / len(utils)
    var = sum((u - mean) ** 2 for u in utils) / len(utils)
    std = var ** 0.5
    kk = max(1, int(0.05 * len(utils)))
    cvar5 = sum(sorted(utils)[:kk]) / kk              # perte moyenne dans les 5% pires
    return {"n": n, "mean": round(mean, 4), "std": round(std, 4),
            "p5": _pct(utils, 5), "p50": _pct(utils, 50), "p95": _pct(utils, 95),
            "cvar5": round(cvar5, 4), "p_faillite": round(bankrupts / n, 3),
            "p_succes": round(successes / n, 3) if goal_id else None}


def monte_carlo_metric(graph: KnowledgeGraph, metric_fn, now: float, *, plan: Plan | None = None,
                       n: int = 2000, seed: int = 0) -> dict:
    """Monte-Carlo sur une MÉTRIQUE scalaire arbitraire (VAN, profit annuel, cadence…).
    `metric_fn(graph) -> float` est évaluée sur chaque futur échantillonné (+ plan/événements).
    Renvoie la distribution + P(métrique < 0)."""
    rng = random.Random(seed)
    vals = []
    for _ in range(n):
        g = _sample(graph, rng)
        if plan is not None:
            for act in plan.actions:
                _apply_effects(g, act.effects)
            for ev in plan.events:
                if rng.random() < ev.probability:
                    _apply_effects(g, [(k, ev.op, v) for k, v in ev.interventions.items()])
            g.recompute()
        vals.append(float(metric_fn(g)))
    mean = sum(vals) / len(vals)
    std = (sum((v - mean) ** 2 for v in vals) / len(vals)) ** 0.5
    return {"n": n, "mean": round(mean, 2), "std": round(std, 2),
            "p5": _pct(vals, 5), "p50": _pct(vals, 50), "p95": _pct(vals, 95),
            "p_negatif": round(sum(1 for v in vals if v < 0) / n, 3)}


def risk_adjusted(dist: dict, risk_aversion: float) -> float:
    """Score = E[U] − λ·σ. λ (aversion) vient de la tolérance au risque de l'objectif :
    λ faible = joueur (favorise l'espérance) ; λ élevé = prudent (pénalise la variance)."""
    return round(dist["mean"] - risk_aversion * dist["std"], 4)


# ---------------------------------------------------------------- Trajectory Ranking (+ garde-fou v1.2)
def _available(graph: KnowledgeGraph, key: str) -> float:
    """Ressource disponible : par ID d'entité Resource précise, sinon par nature (kind)."""
    if key in graph.entities and graph.entities[key].type == "Resource":
        return graph.value(key, "quantite") * (graph.value(key, "disponibilite", 1.0) or 0.0)
    total = 0.0
    for e in graph.entities.values():
        if e.type == "Resource" and e.meta.get("kind") == key:
            total += graph.value(e.id, "quantite") * (graph.value(e.id, "disponibilite", 1.0) or 0.0)
    return total


def feasible_resources(graph: KnowledgeGraph, needs: dict) -> tuple[bool, dict]:
    """Faisabilité GRANULAIRE (v1.2) : un plan qui exige « Ingénieur IA » n'est pas satisfait
    par « un commercial ». Empêche de simuler des projets impossibles."""
    lacks = {k: round(q - _available(graph, k), 3) for k, q in needs.items()
             if _available(graph, k) < q}
    return (not lacks), lacks


def rank_trajectories(graph: KnowledgeGraph, company_id: str, plans: list[Plan], now: float, *,
                      risk_aversion: float = 1.0, n: int = 2000, seed: int = 0,
                      goal_id: str | None = None, bankrupt_below: float = 0.0) -> list[dict]:
    """Classe des HISTOIRES par score ajusté au risque. Un plan infaisable en ressources
    est écarté (jamais une simulation théorique)."""
    out = []
    for i, plan in enumerate(plans):
        ok, lacks = feasible_resources(graph, plan.needs) if plan.needs else (True, {})
        if not ok:
            out.append({"plan": plan.name, "faisable": False, "manque": lacks, "score": None})
            continue
        dist = monte_carlo(graph, company_id, plan, now, n=n, seed=seed + i,
                           goal_id=goal_id, bankrupt_below=bankrupt_below)
        out.append({"plan": plan.name, "faisable": True, "score": risk_adjusted(dist, risk_aversion),
                    "dist": dist})
    out.sort(key=lambda d: (d["faisable"], d["score"] if d["score"] is not None else -9.0), reverse=True)
    return out


# ---------------------------------------------------------------- Apprentissage causal (amorce honnête)
def learn_elasticity(pairs: list[tuple[float, float]]) -> dict:
    """Ajuste y ≈ a·x + b par moindres carrés sur des couples (cause, effet) OBSERVÉS.
    Première brique de l'apprentissage causal : remplacer un coefficient écrit à la main
    par un coefficient APPRIS des résultats réels. (La découverte de structure causale
    complète — quelles arêtes existent — reste un chantier ultérieur.)"""
    n = len(pairs)
    if n < 2:
        return {"a": 0.0, "b": 0.0, "n": n, "r2": 0.0}
    sx = sum(x for x, _ in pairs); sy = sum(y for _, y in pairs)
    sxx = sum(x * x for x, _ in pairs); sxy = sum(x * y for x, y in pairs)
    denom = n * sxx - sx * sx
    if abs(denom) < 1e-12:
        return {"a": 0.0, "b": sy / n, "n": n, "r2": 0.0}
    a = (n * sxy - sx * sy) / denom
    b = (sy - a * sx) / n
    ybar = sy / n
    ss_tot = sum((y - ybar) ** 2 for _, y in pairs)
    ss_res = sum((y - (a * x + b)) ** 2 for x, y in pairs)
    r2 = 1 - ss_res / ss_tot if ss_tot > 1e-12 else 1.0
    return {"a": round(a, 6), "b": round(b, 6), "n": n, "r2": round(r2, 4)}
