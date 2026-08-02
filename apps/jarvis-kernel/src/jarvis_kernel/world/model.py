"""World Model probabiliste — le modèle interne de l'entreprise (l'état S_t).

Chaque nœud est une *croyance* : une valeur, son incertitude (écart-type σ), sa
source, sa date, ses dépendances. Deux opérations font que ce n'est PAS un simple
dictionnaire :

  • observe()  : fusion bayésienne de gaussiennes (précision-pondérée). Une nouvelle
                 mesure ne remplace pas la croyance — elle la met à jour selon la
                 confiance relative des deux. C'est le « Belief Update Engine ».
  • derive()   : nœud calculé (ex. runway = cash / burn) avec PROPAGATION d'incertitude
                 (jacobienne numérique au 1er ordre). L'incertitude se propage dans le graphe.

La confiance rapportée décroît avec le temps (une donnée vieille vaut moins) et
avec σ. Tout est en Python pur (stdlib) — cohérent avec le noyau local-first.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field
from typing import Callable, Iterable

# planchers d'échelle par nature de nœud (pour normaliser σ en « certitude »)
_FLOOR = {"money": 100.0, "count": 1.0, "ratio": 0.05, "flag": 0.15, "metric": 1.0, "months": 0.5}
_HALFLIFE_S = 14 * 86400.0   # une croyance perd la moitié de sa fraîcheur en ~14 jours


@dataclass
class Belief:
    """Un nœud du World Model : une distribution N(value, σ²) datée et sourcée."""
    name: str
    value: float
    sigma: float                 # incertitude (écart-type). Grand σ = « on ne sait pas ».
    source: str = "inconnu"
    ts: float = 0.0              # date de dernière mise à jour (epoch s)
    unit: str = ""
    kind: str = "metric"         # money | count | ratio | flag | months | metric
    depends_on: list[str] = field(default_factory=list)

    def certainty(self) -> float:
        """Certitude issue de σ seul (1 quand σ→0, →0 quand σ énorme)."""
        floor = _FLOOR.get(self.kind, 1.0)
        cv = self.sigma / max(abs(self.value), floor)   # coefficient de variation borné
        return 1.0 / (1.0 + cv)

    def confidence(self, now: float) -> float:
        """Confiance rapportée = certitude (σ) × fraîcheur (âge). Bornée [0,1]."""
        age = max(0.0, now - self.ts)
        freshness = 0.5 ** (age / _HALFLIFE_S)
        return max(0.0, min(1.0, self.certainty() * freshness))


class WorldModel:
    """Graphe de croyances sur l'entreprise. Persistable, fusionnable, dérivable."""

    def __init__(self) -> None:
        self.beliefs: dict[str, Belief] = {}

    # ---- écriture : poser / observer ----
    def set(self, name: str, value: float, sigma: float, *, source: str = "inconnu",
            ts: float = 0.0, unit: str = "", kind: str = "metric",
            depends_on: Iterable[str] | None = None) -> Belief:
        """Pose (ou écrase) une croyance. Pour une *mise à jour* préférer observe()."""
        b = Belief(name=name, value=float(value), sigma=abs(float(sigma)), source=source,
                   ts=float(ts), unit=unit, kind=kind, depends_on=list(depends_on or []))
        self.beliefs[name] = b
        return b

    def observe(self, name: str, value: float, sigma: float, *, source: str = "mesure",
                ts: float = 0.0, unit: str = "", kind: str = "metric") -> Belief:
        """Belief Update : fusion bayésienne de la croyance courante avec la nouvelle
        mesure N(value, σ²). Précision p = 1/σ² ; la mesure la plus sûre pèse le plus.

            μ* = (p₀μ₀ + p₁μ₁) / (p₀+p₁)      σ* = √(1/(p₀+p₁))

        Sans croyance préalable : on adopte la mesure telle quelle."""
        value, sigma = float(value), max(abs(float(sigma)), 1e-9)
        prior = self.beliefs.get(name)
        if prior is None or prior.sigma <= 0:
            return self.set(name, value, sigma, source=source, ts=ts, unit=unit or (prior.unit if prior else ""),
                            kind=kind if not prior else prior.kind)
        p0, p1 = 1.0 / (prior.sigma ** 2), 1.0 / (sigma ** 2)
        mu = (p0 * prior.value + p1 * value) / (p0 + p1)
        sig = math.sqrt(1.0 / (p0 + p1))
        prior.value, prior.sigma = mu, sig
        prior.source = f"{prior.source}+{source}" if source not in prior.source else prior.source
        prior.ts = max(prior.ts, ts)
        return prior

    # ---- dérivation : nœud calculé avec propagation d'incertitude ----
    def derive(self, name: str, fn: Callable[[dict[str, float]], float], inputs: list[str],
               *, source: str = "dérivé", unit: str = "", kind: str = "metric") -> Belief:
        """Nœud = fn(entrées) ; σ propagé par jacobienne numérique au 1er ordre :
            σ² ≈ Σ (∂fn/∂xᵢ)² σᵢ²   (dérivées partielles par différences finies)."""
        means = {i: self.beliefs[i].value for i in inputs}
        base = float(fn(means))
        var = 0.0
        ts = 0.0
        for i in inputs:
            b = self.beliefs[i]
            ts = max(ts, b.ts)
            h = (abs(b.sigma) or abs(b.value) or 1.0) * 1e-4 + 1e-9
            up = dict(means); up[i] = means[i] + h
            deriv = (float(fn(up)) - base) / h
            var += (deriv * b.sigma) ** 2
        return self.set(name, base, math.sqrt(var), source=source, ts=ts, unit=unit,
                        kind=kind, depends_on=list(inputs))

    # ---- lecture ----
    def get(self, name: str) -> Belief | None:
        return self.beliefs.get(name)

    def value(self, name: str, default: float = 0.0) -> float:
        b = self.beliefs.get(name)
        return b.value if b else default

    def snapshot(self, now: float) -> list[dict]:
        """État lisible, trié par confiance décroissante — pour l'UI / l'audit."""
        rows = []
        for b in self.beliefs.values():
            rows.append({"name": b.name, "value": round(b.value, 4), "sigma": round(b.sigma, 4),
                         "confidence": round(b.confidence(now), 3), "unit": b.unit,
                         "kind": b.kind, "source": b.source, "depends_on": b.depends_on})
        rows.sort(key=lambda r: r["confidence"], reverse=True)
        return rows

    # ---- persistance ----
    def to_dict(self) -> dict:
        return {"beliefs": [asdict(b) for b in self.beliefs.values()]}

    @classmethod
    def from_dict(cls, data: dict | None) -> "WorldModel":
        w = cls()
        for row in (data or {}).get("beliefs", []):
            row = {k: v for k, v in row.items() if k in Belief.__annotations__}
            b = Belief(**row)
            w.beliefs[b.name] = b
        return w

    def save(self, memory, namespace: str = "world") -> None:
        memory.remember("state", self.to_dict(), namespace=namespace)

    @classmethod
    def load(cls, memory, namespace: str = "world") -> "WorldModel":
        return cls.from_dict(memory.recall("state", namespace=namespace))
