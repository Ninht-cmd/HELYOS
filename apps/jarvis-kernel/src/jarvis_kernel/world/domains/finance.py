"""Domaine FINANCE — les vraies lois financières (accounting, valuation).

Équations standard et correctes (testées) : marge brute, runway, ROI, VAN (NPV),
TRI (IRR) par bissection, délai de récupération. Injecte le type ``BusinessUnit``.
"""

from __future__ import annotations

from ..ontology import AttrSpec, EntityType
from . import Domain

_A = AttrSpec.of


# ------------------------------------------------------------------ équations
def gross_margin(revenue: float, cogs: float) -> float:
    """Marge brute = (CA − coûts des ventes) / CA."""
    return (revenue - cogs) / revenue if revenue else 0.0


def runway_months(cash: float, monthly_burn: float) -> float:
    """Runway (mois) = trésorerie / consommation mensuelle."""
    return cash / monthly_burn if monthly_burn > 0 else float("inf")


def roi(gain: float, investment: float) -> float:
    """Retour sur investissement = (gain − investissement) / investissement."""
    return (gain - investment) / investment if investment else 0.0


def npv(rate: float, cashflows: list[float]) -> float:
    """Valeur actuelle nette : Σ CF_t / (1+r)^t, t = 0..n (CF_0 souvent négatif = CAPEX)."""
    return sum(cf / ((1.0 + rate) ** t) for t, cf in enumerate(cashflows))


def irr(cashflows: list[float], lo: float = -0.9999, hi: float = 10.0, iters: int = 200):
    """Taux de rentabilité interne : le taux r tel que VAN(r) = 0 (bissection).
    Renvoie None s'il n'existe pas de changement de signe sur [lo, hi]."""
    flo, fhi = npv(lo, cashflows), npv(hi, cashflows)
    if flo == 0:
        return lo
    if flo * fhi > 0:
        return None
    for _ in range(iters):
        mid = (lo + hi) / 2.0
        fm = npv(mid, cashflows)
        if abs(fm) < 1e-12:
            return mid
        if flo * fm < 0:
            hi = mid
        else:
            lo, flo = mid, fm
    return (lo + hi) / 2.0


def payback_period(cashflows: list[float]):
    """Délai de récupération : premier t où le cumul des flux devient ≥ 0. None sinon."""
    cum = 0.0
    for t, cf in enumerate(cashflows):
        cum += cf
        if cum >= 0:
            return t
    return None


# ------------------------------------------------------------------ domaine
FINANCE = Domain(
    name="finance",
    entity_types={
        "BusinessUnit": EntityType("BusinessUnit",
            {a.name: a for a in [
                _A("capex", "money", "€"), _A("opex", "money", "€/mois"),
                _A("revenus", "money", "€/mois"), _A("couts", "money", "€/mois"),
                _A("marge_brute", "ratio"), _A("cash", "money", "€"),
                _A("runway_mois", "months", "mois"), _A("roi", "ratio"),
                _A("risque_faillite", "ratio")]},
            "Une unité d'affaires (P&L, CAPEX/OPEX, valorisation)"),
    },
    equations={"gross_margin": gross_margin, "runway_months": runway_months, "roi": roi,
               "npv": npv, "irr": irr, "payback_period": payback_period},
)


def wire_finance(graph, bu_id: str) -> None:
    """Attache les lois financières à une BusinessUnit : marge brute et runway dérivés."""
    k = graph.key
    graph.derive_attr(bu_id, "marge_brute",
                      lambda m: gross_margin(m[k(bu_id, "revenus")], m[k(bu_id, "couts")]),
                      [k(bu_id, "revenus"), k(bu_id, "couts")])
    if graph.attr(bu_id, "cash") is not None and graph.attr(bu_id, "opex") is not None:
        graph.derive_attr(bu_id, "runway_mois",
                          lambda m: min(999.0, m[k(bu_id, "cash")] / max(m[k(bu_id, "opex")], 1e-6)),
                          [k(bu_id, "cash"), k(bu_id, "opex")])
