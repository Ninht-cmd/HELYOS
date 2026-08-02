"""HELYOS Learning Loop — fermer la boucle simulation ↔ réalité.

Jusqu'ici les lois causales (ex. coût ≈ 1.6·prix) étaient écrites par le développeur.
Ici HELYOS les APPREND des résultats réels :

    Observation → Knowledge Graph → Simulation → Décision → Exécution → Résultat réel
        → mesure de l'erreur → mise à jour des coefficients → nouveau modèle du monde.

Cœur : une loi causale ``y ≈ a·x`` dont le coefficient ``a`` est une CROYANCE gaussienne
``N(mean, σ²)`` mise à jour par **régression bayésienne récursive** (conjuguée, bruit
d'observation connu) — exacte, une observation à la fois, avec réduction d'incertitude.

Portée honnête : on apprend la VALEUR d'une loi dont la FORME (quelles variables, quel
lien) est donnée. La découverte de structure (quelles arêtes causales existent) reste un
chantier distinct.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass
class CausalLaw:
    """Loi causale apprise ``y ≈ a·x`` (pente à l'origine). ``a`` est une croyance
    gaussienne ; ``noise_sigma`` = bruit d'observation supposé sur ``y``."""
    name: str
    x_key: str
    y_key: str
    coef_mean: float = 1.0
    coef_sigma: float = 1.0        # incertitude sur a (grand σ = a priori faible)
    noise_sigma: float = 1.0       # écart-type du bruit d'observation sur y (connu)
    n_obs: int = 0

    def predict(self, x: float) -> tuple[float, float]:
        """ŷ et son incertitude : σ² = (x·σ_a)² + σ_bruit² (incertitude du coefficient + bruit)."""
        mean = self.coef_mean * x
        sigma = math.sqrt((x * self.coef_sigma) ** 2 + self.noise_sigma ** 2)
        return mean, sigma

    def observe(self, x: float, y: float) -> tuple[float, float]:
        """Mise à jour bayésienne conjuguée de ``a`` avec une observation (x, y) :
            p_post = p_prior + x²/σ_bruit²
            mean_post = (p_prior·mean + x·y/σ_bruit²) / p_post,  σ_post = √(1/p_post).
        Chaque observation resserre l'incertitude sur a."""
        nz2 = max(self.noise_sigma ** 2, 1e-12)
        p_prior = 1.0 / max(self.coef_sigma ** 2, 1e-12)
        p_post = p_prior + (x * x) / nz2
        self.coef_mean = (p_prior * self.coef_mean + (x * y) / nz2) / p_post
        self.coef_sigma = math.sqrt(1.0 / p_post)
        self.n_obs += 1
        return self.coef_mean, self.coef_sigma


def calibration(law: CausalLaw, pairs: list[tuple[float, float]]) -> dict:
    """Mesure la qualité du modèle sur des couples (x, y_réel) : MAE, RMSE, biais, et
    COUVERTURE (fraction des réels dans ±1σ prédit ; ~0.68 si bien calibré)."""
    if not pairs:
        return {"mae": 0.0, "rmse": 0.0, "bias": 0.0, "coverage": 0.0, "n": 0}
    errs, covered = [], 0
    for x, y in pairs:
        mean, sigma = law.predict(x)
        e = y - mean
        errs.append(e)
        if abs(e) <= sigma:
            covered += 1
    n = len(pairs)
    return {"mae": round(sum(abs(e) for e in errs) / n, 4),
            "rmse": round((sum(e * e for e in errs) / n) ** 0.5, 4),
            "bias": round(sum(errs) / n, 4),
            "coverage": round(covered / n, 3), "n": n}


def close_loop(law: CausalLaw, stream: list[tuple[float, float]]) -> list[dict]:
    """LA BOUCLE : pour chaque (x, y_réel) — PRÉDIRE (avant d'apprendre), MESURER l'erreur,
    puis METTRE À JOUR le coefficient. Renvoie la trajectoire (coef, σ, erreur) : la preuve
    que le modèle s'améliore."""
    traj = []
    for i, (x, y) in enumerate(stream, 1):
        pred, _ = law.predict(x)         # 1) prédire avec le modèle courant
        err = y - pred                    # 2) mesurer l'écart au réel
        law.observe(x, y)                 # 3) apprendre (mise à jour du coefficient)
        traj.append({"pas": i, "predit": round(pred, 3), "reel": round(y, 3),
                     "erreur": round(err, 3), "coef": round(law.coef_mean, 4),
                     "coef_sigma": round(law.coef_sigma, 4)})
    return traj


# ------------------------------------------------------- intégration au Knowledge Graph
def wire_learned(graph, law: CausalLaw) -> None:
    """Branche la loi apprise comme dérivation : y_attr = coef_mean · x_key. Re-dériver
    après apprentissage met à jour le modèle du monde (le graphe suit le coefficient)."""
    ent, attr = law.y_key.split(".", 1)
    graph.derive_attr(ent, attr, lambda m, L=law: L.coef_mean * m[L.x_key], [law.x_key])


def relearn(graph, law: CausalLaw, pairs: list[tuple[float, float]]) -> float:
    """Apprend de nouvelles observations puis RE-DÉRIVE le graphe : le monde s'auto-corrige."""
    for x, y in pairs:
        law.observe(x, y)
    graph.recompute()
    return law.coef_mean
