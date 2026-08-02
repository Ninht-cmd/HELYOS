"""Fonction d'utilité explicite U(S) + politique de décision π = argmax E[U].

C'est ici qu'HELYOS cesse de « répondre » pour « décider » :

  1. U(S)   : un scalaire explicite et inspectable sur l'état du monde. Chaque terme
             est pondéré par la CONFIANCE de la croyance — on n'agit pas fort sur une
             donnée incertaine. Rien de caché : la décomposition est renvoyée.
  2. decide : pour chaque action candidate, on applique son modèle d'effet à une COPIE
             du World Model, on recalcule U, et on classe par gain d'utilité espéré
             (ΔU) moins le coût. C'est la politique de contrôle en germe.

Le LLM n'intervient pas dans ce calcul : il pourra *proposer* des croyances ou des
actions (estimateur), mais l'arbitrage est numérique. Python pur.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from .model import WorldModel

# Cibles explicites de la fonction d'utilité (le « cap » de normalisation).
# Ce sont les objectifs du fondateur, tunables — pas des constantes magiques cachées.
TARGET_CASH = 100_000.0     # objectif net visé (€)
TARGET_REV = 10_000.0       # revenu mensuel « sain » (€)
RUNWAY_FULL_MONTHS = 12.0

# Poids de la fonction d'utilité (somme des positifs = 1 ; le risque est un malus).
WEIGHTS = {
    "cash": 0.30, "revenu": 0.25, "runway": 0.15,
    "progres": 0.20, "clients": 0.10, "risque": 0.35,
}


def _term(world: WorldModel, name: str, now: float, cap: float, floor0: float = 0.0):
    """Renvoie (valeur_normalisée ∈ [0,1], confiance) pour une croyance, 0 si absente."""
    b = world.get(name)
    if b is None:
        return 0.0, 0.0
    norm = max(floor0, min(1.0, b.value / cap)) if cap else b.value
    return norm, b.confidence(now)


def _risk(world: WorldModel, now: float) -> tuple[float, float]:
    """Risque agrégé ∈ [0,1] : moyenne des risques connus, pondérée par leur confiance."""
    parts = [world.get(n) for n in ("risque_paiement", "risque_legal", "risque_ops")]
    parts = [b for b in parts if b is not None]
    if not parts:
        b = world.get("risque")
        return (b.value, b.confidence(now)) if b else (0.0, 0.0)
    conf = sum(b.confidence(now) for b in parts) / len(parts)
    return sum(max(0.0, min(1.0, b.value)) for b in parts) / len(parts), conf


def utility(world: WorldModel, now: float, weights: dict | None = None):
    """U(S) explicite. Renvoie (score, décomposition[]). Chaque contribution =
    valeur_normalisée × poids × confiance (le risque est soustrait)."""
    w = weights or WEIGHTS
    rows = []

    def add(term, norm, conf, weight, sign=1):
        contrib = sign * weight * norm * conf
        rows.append({"terme": term, "valeur": round(norm, 3), "poids": weight,
                     "confiance": round(conf, 3), "contribution": round(contrib, 4)})
        return contrib

    score = 0.0
    score += add("cash", *_term(world, "cash", now, TARGET_CASH), w["cash"])
    score += add("revenu", *_term(world, "revenu_mensuel", now, TARGET_REV), w["revenu"])
    score += add("runway", *_term(world, "runway_mois", now, RUNWAY_FULL_MONTHS), w["runway"])
    score += add("progres", *_term(world, "progres_objectif", now, 1.0), w["progres"])
    score += add("clients", *_term(world, "clients", now, 10.0), w["clients"])
    rnorm, rconf = _risk(world, now)
    score += add("risque", rnorm, rconf, w["risque"], sign=-1)
    return round(score, 4), rows


@dataclass
class Action:
    """Une action candidate + son modèle d'effet sur l'état (forward model)."""
    name: str
    description: str = ""
    cost: float = 0.0                         # pénalité d'utilité (effort/€), en unités d'U
    effects: list[tuple[str, str, float]] = field(default_factory=list)  # (croyance, op, montant)
    # op ∈ {"add","set","mul"} ; appliqué à la VALEUR moyenne de la croyance

    def apply(self, world: WorldModel) -> None:
        for name, op, amt in self.effects:
            b = world.get(name)
            if b is None:
                # une action peut créer un nœud (ex. premier client -> clients=1)
                world.set(name, amt if op != "mul" else 0.0, sigma=abs(amt) * 0.1 + 0.1,
                          source="effet_action", kind="metric")
                continue
            if op == "add":
                b.value += amt
            elif op == "set":
                b.value = amt
            elif op == "mul":
                b.value *= amt


@dataclass
class Decision:
    action: Action
    gain: float               # ΔU espéré (net du coût)
    u_before: float
    u_after: float
    rationale: str


class Policy:
    """π : classe les actions candidates par utilité espérée. argmax E[U] borné."""

    def decide(self, world: WorldModel, actions: list[Action], now: float) -> list[Decision]:
        u0, base = utility(world, now)
        base_by = {r["terme"]: r["contribution"] for r in base}
        out: list[Decision] = []
        for a in actions:
            clone = WorldModel.from_dict(world.to_dict())
            a.apply(clone)
            u1, after = utility(clone, now)
            gain = round(u1 - u0 - a.cost, 4)
            # rationale : le terme d'utilité qui bouge le plus
            moved = max(after, key=lambda r: abs(r["contribution"] - base_by.get(r["terme"], 0.0)))
            delta = moved["contribution"] - base_by.get(moved["terme"], 0.0)
            rationale = (f"{'+' if delta >= 0 else ''}{round(delta, 3)} sur « {moved['terme']} »"
                         + (f", coût {a.cost}" if a.cost else ""))
            out.append(Decision(a, gain, u0, round(u1, 4), rationale))
        out.sort(key=lambda d: d.gain, reverse=True)
        return out
