"""Supply Chain OS — un Domain OS COMPLET, traité comme un modèle scientifique gouverné.

Couvre de bout en bout (les 8 points) : fournisseurs & contrats, stocks, capacité,
délais & logistique, événements, simulation Monte-Carlo, apprentissage sur les
performances observées, gouvernance des lois apprises.

Cœur = la science des stocks (inventory theory), exacte et validée :
  • demande pendant le délai (DLT) à délai stochastique ;
  • stock de sécurité, point de commande, EOQ ;
  • fonction de perte normale L(z), rupture espérée, taux de service (fill rate) ;
  • coût total (possession + commande + rupture) ; taux d'utilisation capacité.

L'apprentissage (délai réel appris) et la gouvernance (versions, dérive, rollback)
se font en composant avec `learning.CausalLaw` et `registry.ModelRegistry` — le
domaine PLUGE dans le noyau, il ne le duplique pas.
"""

from __future__ import annotations

import math
import random

from ..ontology import AttrSpec, EntityType
from . import Domain
from .trading import norm_cdf, norm_pdf, norm_ppf     # gaussiennes générales (foyer canonique)

_A = AttrSpec.of


# ------------------------------------------------------------------ science des stocks
def lead_time_demand_std(demand: float, sigma_demand: float, lead_time: float,
                         sigma_lead_time: float) -> float:
    """Écart-type de la demande pendant le délai (délai stochastique) :
        σ_DLT = √(LT·σ_d² + d²·σ_LT²)."""
    return math.sqrt(lead_time * sigma_demand ** 2 + demand ** 2 * sigma_lead_time ** 2)


def service_level_z(service_level: float) -> float:
    """Facteur de sécurité z correspondant à un taux de service cyclique (ex. 0.95 → 1.645)."""
    return norm_ppf(service_level)


def safety_stock(z: float, sigma_dlt: float) -> float:
    """Stock de sécurité = z · σ_DLT."""
    return z * sigma_dlt


def reorder_point(demand: float, lead_time: float, safety: float) -> float:
    """Point de commande = demande moyenne pendant le délai + stock de sécurité."""
    return demand * lead_time + safety


def eoq(annual_demand: float, order_cost: float, holding_cost: float) -> float:
    """Quantité économique de commande (Wilson) : √(2·D·S / H)."""
    return math.sqrt(2.0 * annual_demand * order_cost / holding_cost) if holding_cost > 0 else 0.0


def normal_loss(z: float) -> float:
    """Fonction de perte normale standard : L(z) = φ(z) − z·(1 − Φ(z))."""
    return norm_pdf(z) - z * (1.0 - norm_cdf(z))


def expected_shortage(sigma_dlt: float, z: float) -> float:
    """Rupture espérée par cycle = σ_DLT · L(z)."""
    return sigma_dlt * normal_loss(z)


def fill_rate(sigma_dlt: float, z: float, order_qty: float) -> float:
    """Taux de service (fill rate) = 1 − rupture espérée par cycle / quantité commandée."""
    return 1.0 - expected_shortage(sigma_dlt, z) / order_qty if order_qty > 0 else 0.0


def total_inventory_cost(holding_cost: float, safety: float, order_qty: float,
                         order_cost: float, annual_demand: float,
                         stockout_cost: float = 0.0, exp_shortage: float = 0.0) -> float:
    """Coût annuel total = possession (SS + Q/2) + commandes (D/Q) + ruptures."""
    cycles = annual_demand / order_qty if order_qty > 0 else 0.0
    return (holding_cost * (safety + order_qty / 2.0)
            + order_cost * cycles
            + stockout_cost * exp_shortage * cycles)


def capacity_utilization(demand_rate: float, capacity: float) -> float:
    """Taux d'utilisation = débit demandé / capacité."""
    return demand_rate / capacity if capacity > 0 else float("inf")


# ------------------------------------------------------------------ simulation Monte-Carlo (domaine)
def simulate_service_level(mean_dlt: float, sigma_dlt: float, rop: float, *,
                           n: int = 5000, seed: int = 0) -> dict:
    """Tire N cycles : demande pendant le délai ~ N(mean_dlt, σ_dlt²) ; rupture si DLT > point
    de commande. Renvoie le taux de service atteint, la fréquence de rupture, la rupture moyenne.
    Sert à VALIDER qu'un point de commande calculé tient réellement (auto-cohérence)."""
    rng = random.Random(seed)
    stockouts, shortage_sum = 0, 0.0
    for _ in range(n):
        dlt = rng.gauss(mean_dlt, sigma_dlt)
        if dlt > rop:
            stockouts += 1
            shortage_sum += dlt - rop
    return {"n": n, "service_level": round(1 - stockouts / n, 4),
            "stockout_prob": round(stockouts / n, 4),
            "mean_shortage": round(shortage_sum / n, 3)}


def service_level_distribution(mean_dlt: float, sigma_dlt: float, rop: float, *,
                               n: int = 20000, seed: int = 0, bins: int = 24) -> dict:
    """Distribution complète de la demande pendant le délai (pour la visualisation) :
    histogramme, P5/P50/P95, et niveau de service atteint face au point de commande."""
    rng = random.Random(seed)
    samples = [rng.gauss(mean_dlt, sigma_dlt) for _ in range(n)]
    lo, hi = min(samples), max(samples)
    width = (hi - lo) / bins or 1.0
    counts = [0] * bins
    for s in samples:
        counts[min(bins - 1, int((s - lo) / width))] += 1
    ss = sorted(samples)
    pct = lambda p: ss[min(n - 1, int(p / 100 * (n - 1)))]
    service = sum(1 for s in samples if s <= rop) / n
    return {"lo": round(lo, 2), "hi": round(hi, 2), "width": round(width, 3), "bins": bins,
            "counts": counts, "p5": round(pct(5), 2), "p50": round(pct(50), 2),
            "p95": round(pct(95), 2), "service_level": round(service, 4),
            "rop": round(rop, 2), "mean_dlt": round(mean_dlt, 2)}


# ------------------------------------------------------------------ domaine + cas de référence
SUPPLY_CHAIN = Domain(
    name="supply_chain",
    entity_types={
        "Supplier": EntityType("Supplier",
            {a.name: a for a in [
                _A("lead_time_mean", "metric", "j"), _A("lead_time_std", "metric", "j"),
                _A("reliability", "ratio")]},
            "Fournisseur (enrichi : délai moyen/écart-type, fiabilité)"),
        "Stock": EntityType("Stock",
            {a.name: a for a in [
                _A("demand_mean", "metric", "u/j"), _A("demand_std", "metric", "u/j"),
                _A("on_hand", "count", "u"), _A("safety_stock", "count", "u"),
                _A("reorder_point", "count", "u"), _A("eoq", "count", "u"),
                _A("holding_cost", "money", "€/u/an"), _A("order_cost", "money", "€"),
                _A("stockout_cost", "money", "€/u"), _A("fill_rate", "ratio")]},
            "Stock d'un article (politique de réapprovisionnement)"),
        "Capacity": EntityType("Capacity",
            {a.name: a for a in [_A("capacite", "metric", "u/j"), _A("utilisation", "ratio")]},
            "Capacité de production"),
        "Shipment": EntityType("Shipment",
            {a.name: a for a in [_A("cout_transport", "money", "€"), _A("delai_jours", "count", "j"),
                                 _A("risque_retard", "ratio")]},
            "Expédition / logistique"),
    },
    equations={"lead_time_demand_std": lead_time_demand_std, "service_level_z": service_level_z,
               "safety_stock": safety_stock, "reorder_point": reorder_point, "eoq": eoq,
               "normal_loss": normal_loss, "expected_shortage": expected_shortage,
               "fill_rate": fill_rate, "total_inventory_cost": total_inventory_cost,
               "capacity_utilization": capacity_utilization},
    reference_cases=[
        {"equation": "eoq", "kwargs": {"annual_demand": 1000, "order_cost": 50, "holding_cost": 2},
         "expected": 223.607, "tol": 1e-2},                         # √(2·1000·50/2) = √50000
        {"equation": "normal_loss", "kwargs": {"z": 0.0}, "expected": 0.39894, "tol": 1e-4},   # φ(0)
        {"equation": "normal_loss", "kwargs": {"z": 1.645}, "expected": 0.020862, "tol": 1e-4},
        {"equation": "safety_stock", "kwargs": {"z": 1.645, "sigma_dlt": 100}, "expected": 164.5, "tol": 1e-6},
    ],
)


# ------------------------------------------------------------------ politique de bout en bout
def inventory_policy(demand: float, sigma_demand: float, lead_time: float, sigma_lead_time: float,
                     service_level: float, annual_demand: float, order_cost: float,
                     holding_cost: float, stockout_cost: float = 0.0) -> dict:
    """Calcule une politique complète (SS, ROP, EOQ, fill rate, coût) à partir des paramètres
    de demande, de délai et de coûts. C'est la décision opérationnelle du Supply Chain OS."""
    sig_dlt = lead_time_demand_std(demand, sigma_demand, lead_time, sigma_lead_time)
    z = service_level_z(service_level)
    ss = safety_stock(z, sig_dlt)
    rop = reorder_point(demand, lead_time, ss)
    q = eoq(annual_demand, order_cost, holding_cost)
    fr = fill_rate(sig_dlt, z, q)
    shortage = expected_shortage(sig_dlt, z)
    cost = total_inventory_cost(holding_cost, ss, q, order_cost, annual_demand, stockout_cost, shortage)
    return {"sigma_dlt": round(sig_dlt, 2), "z": round(z, 3), "safety_stock": round(ss, 1),
            "reorder_point": round(rop, 1), "eoq": round(q, 1), "fill_rate": round(fr, 4),
            "expected_shortage": round(shortage, 2), "total_cost": round(cost, 2)}
