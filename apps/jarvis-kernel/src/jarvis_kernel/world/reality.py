"""HELYOS Reality Layer v1.1 — ce qui transforme un noyau en organisme.

Au-dessus de l'ontologie (les objets du monde), la Reality Layer ajoute ce sans quoi
on ne peut pas *planifier ni réagir* :

  • Resource Model  : quelles ressources (financières/humaines/matérielles/numériques)
                      sont disponibles → FAISABILITÉ d'une action.
  • Goal System     : un objectif est une entité de première classe avec des métriques
                      cibles → on mesure l'ATTEINTE.
  • Event System    : un événement = une intervention do(x=v) qui se PROPAGE dans le
                      graphe causal (réutilise KnowledgeGraph.simulate).
  • Boucle réactive : Événement → propagation → NOUVELLE DÉCISION (respond).
  • Rollout H=N     : appliquer une SÉQUENCE d'événements/actions et lire la trajectoire
                      d'utilité. Premier étage vers la simulation Monte-Carlo (v1.3).

Tout est chiffré et réutilise la colonne vertébrale probabiliste (croyances μ±σ).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .ontology import KnowledgeGraph

# ---------------------------------------------------------------- Resource Model
def resource_pool(graph: KnowledgeGraph) -> dict[str, float]:
    """Ressources disponibles par nature (``Entity.meta['kind']``), pondérées par la
    disponibilité. kind ∈ financial|human|material|digital."""
    pool: dict[str, float] = {}
    for e in graph.entities.values():
        if e.type != "Resource":
            continue
        kind = e.meta.get("kind", "autre")
        qty = graph.value(e.id, "quantite") * (graph.value(e.id, "disponibilite", 1.0) or 0.0)
        pool[kind] = pool.get(kind, 0.0) + qty
    return pool


def feasible(graph: KnowledgeGraph, needs: dict[str, float]) -> tuple[bool, dict[str, float]]:
    """`needs` = {kind: quantité}. Renvoie (faisable, manques). Sans ressources, pas de plan."""
    pool = resource_pool(graph)
    lacks = {k: round(q - pool.get(k, 0.0), 3) for k, q in needs.items() if pool.get(k, 0.0) < q}
    return (not lacks), lacks


# ---------------------------------------------------------------- Goal System
def goal_attainment(graph: KnowledgeGraph, goal_id: str, now: float) -> float:
    """Atteinte ∈ [0,1] d'un Goal via ses métriques cibles (``meta['targets']`` =
    {clé_de_croyance: valeur_cible}). À défaut, l'attribut `progres`."""
    g = graph._entity(goal_id)
    targets = g.meta.get("targets", {})
    if not targets:
        return round(graph.value(goal_id, "progres"), 3)
    ratios = []
    for key, target in targets.items():
        b = graph.world.get(key)
        if b is None or not target:
            continue
        ratios.append(max(0.0, min(1.0, b.value / target)))
    return round(sum(ratios) / len(ratios), 3) if ratios else 0.0


# ---------------------------------------------------------------- Utilité par entité
COMPANY_WEIGHTS = {"cash": 0.25, "marge": 0.25, "croissance": 0.15, "runway": 0.15, "risque": 0.30}
_CAP = {"cash": 100_000.0, "marge": 1.0, "croissance": 1.0, "runway_mois": 12.0, "risque": 1.0}


def company_utility(graph: KnowledgeGraph, company_id: str, now: float):
    """Utilité d'une entreprise sur ses propres attributs (confiance-pondérée).
    Renvoie (score, décomposition)."""
    w, rows, score = COMPANY_WEIGHTS, [], 0.0

    def term(attr: str, weight: float, sign: int = 1) -> float:
        b = graph.attr(company_id, attr)
        if b is None:
            return 0.0
        cap = _CAP.get(attr, 1.0)
        norm = max(0.0, min(1.0, b.value / cap)) if cap else b.value
        conf = b.confidence(now)
        contrib = sign * weight * norm * conf
        rows.append({"terme": attr, "valeur": round(norm, 3), "confiance": round(conf, 3),
                     "contribution": round(contrib, 4)})
        return contrib

    score += term("cash", w["cash"])
    score += term("marge", w["marge"])
    score += term("croissance", w["croissance"])
    score += term("runway_mois", w["runway"])
    score += term("risque", w["risque"], sign=-1)
    return round(score, 4), rows


# ---------------------------------------------------------------- Event System
def apply_event(graph: KnowledgeGraph, interventions: dict[str, float], now: float) -> dict:
    """Un événement change le monde : do(interventions) → propagation causale. Renvoie
    les nœuds touchés (avant/après/σ). Mute le graphe (l'événement a eu lieu)."""
    return graph.simulate(interventions, now=now)


# ---------------------------------------------------------------- Décision après événement
@dataclass
class Response:
    name: str
    effects: list[tuple[str, str, float]] = field(default_factory=list)   # (clé, op, montant)
    cost: float = 0.0
    needs: dict = field(default_factory=dict)                             # {kind: quantité}


def respond(graph: KnowledgeGraph, company_id: str, options: list[Response], now: float) -> list[dict]:
    """Après un événement : classe les réponses par ΔU d'entreprise, en écartant les
    infaisables (ressources). C'est la NOUVELLE DÉCISION déclenchée par l'événement."""
    u0, _ = company_utility(graph, company_id, now)
    out = []
    for opt in options:
        ok, lacks = feasible(graph, opt.needs) if opt.needs else (True, {})
        if not ok:
            out.append({"action": opt.name, "gain": None, "faisable": False, "manque": lacks})
            continue
        g = graph.clone()
        for key, op, amt in opt.effects:
            b = g.world.get(key)
            if b is None:
                continue
            b.value = amt if op == "set" else (b.value + amt if op == "add" else b.value * amt)
        g.recompute()
        u1, _ = company_utility(g, company_id, now)
        out.append({"action": opt.name, "gain": round(u1 - u0 - opt.cost, 4), "faisable": True})
    out.sort(key=lambda d: (d["faisable"], d["gain"] if d["gain"] is not None else -9.0), reverse=True)
    return out


# ---------------------------------------------------------------- Rollout H=N
def rollout(graph: KnowledgeGraph, company_id: str, steps: list[tuple[str, dict]], now: float) -> list[dict]:
    """Applique une SÉQUENCE (label, interventions) et renvoie la trajectoire d'utilité.
    Rollout déterministe multi-pas (H=N) — 1er étage ; le Monte-Carlo à N futurs = v1.3."""
    g = graph.clone()
    traj = [{"pas": 0, "label": "état initial", "u": company_utility(g, company_id, now)[0]}]
    for i, (label, interventions) in enumerate(steps, 1):
        g.simulate(interventions, now=now)
        traj.append({"pas": i, "label": label, "u": round(company_utility(g, company_id, now)[0], 4)})
    return traj
