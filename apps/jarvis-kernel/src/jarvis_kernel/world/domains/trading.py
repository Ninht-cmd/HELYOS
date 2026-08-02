"""Domaine TRADING — profondeur quant de niveau professionnel (preuve de scalabilité).

But : montrer que le framework de domaines accepte une VRAIE profondeur métier — pas
« Position/Asset/Market » mais des lois exactes : Black-Scholes + Greeks (Δ Γ Θ Vega Rho),
VaR (historique & paramétrique), Expected Shortfall (CVaR), ratio de Sharpe, volatilité de
portefeuille (covariance), bêta. Python pur (stdlib `math` seule).

Ce domaine est UN lobe ; la largeur complète d'un système de trading pro (carnet d'ordres,
surface de vol implicite, financement, régimes, coûts de transaction…) reste le gros du
travail — c'est précisément le 80–90 % « connaissance métier » hors du noyau.
"""

from __future__ import annotations

import math

from ..ontology import AttrSpec, EntityType
from . import Domain

_A = AttrSpec.of
_SQRT2PI = math.sqrt(2.0 * math.pi)


# ------------------------------------------------------------------ lois gaussiennes
def norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def norm_pdf(x: float) -> float:
    return math.exp(-0.5 * x * x) / _SQRT2PI


def norm_ppf(p: float) -> float:
    """Quantile de la loi normale standard (approximation d'Acklam, ~1e-9)."""
    if not 0.0 < p < 1.0:
        raise ValueError("p ∈ ]0,1[")
    a = [-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02,
         1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00]
    b = [-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02,
         6.680131188771972e+01, -1.328068155288572e+01]
    c = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00,
         -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00]
    d = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00,
         3.754408661907416e+00]
    plow, phigh = 0.02425, 1 - 0.02425
    if p < plow:
        q = math.sqrt(-2 * math.log(p))
        return (((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
    if p > phigh:
        q = math.sqrt(-2 * math.log(1 - p))
        return -(((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
    q = p - 0.5
    r = q * q
    return (((((a[0]*r+a[1])*r+a[2])*r+a[3])*r+a[4])*r+a[5])*q / (((((b[0]*r+b[1])*r+b[2])*r+b[3])*r+b[4])*r+1)


# ------------------------------------------------------------------ options : Black-Scholes + Greeks
def _d1_d2(S, K, r, sigma, T):
    d1 = (math.log(S / K) + (r + 0.5 * sigma * sigma) * T) / (sigma * math.sqrt(T))
    return d1, d1 - sigma * math.sqrt(T)


def black_scholes(S: float, K: float, r: float, sigma: float, T: float, kind: str = "call") -> float:
    """Prix Black-Scholes d'une option européenne."""
    d1, d2 = _d1_d2(S, K, r, sigma, T)
    if kind == "call":
        return S * norm_cdf(d1) - K * math.exp(-r * T) * norm_cdf(d2)
    return K * math.exp(-r * T) * norm_cdf(-d2) - S * norm_cdf(-d1)


def greeks(S: float, K: float, r: float, sigma: float, T: float, kind: str = "call") -> dict:
    """Sensibilités : delta, gamma, vega (par unité de σ), theta (par an), rho."""
    d1, d2 = _d1_d2(S, K, r, sigma, T)
    pdf, srt = norm_pdf(d1), math.sqrt(T)
    gamma = pdf / (S * sigma * srt)
    vega = S * pdf * srt
    if kind == "call":
        delta = norm_cdf(d1)
        theta = -(S * pdf * sigma) / (2 * srt) - r * K * math.exp(-r * T) * norm_cdf(d2)
        rho = K * T * math.exp(-r * T) * norm_cdf(d2)
    else:
        delta = norm_cdf(d1) - 1.0
        theta = -(S * pdf * sigma) / (2 * srt) + r * K * math.exp(-r * T) * norm_cdf(-d2)
        rho = -K * T * math.exp(-r * T) * norm_cdf(-d2)
    return {"delta": delta, "gamma": gamma, "vega": vega, "theta": theta, "rho": rho}


# ------------------------------------------------------------------ risque de marché
def parametric_var(mu: float, sigma: float, level: float = 0.95) -> float:
    """VaR paramétrique (perte positive) au niveau `level` sous hypothèse gaussienne."""
    return -(mu + norm_ppf(1 - level) * sigma)


def parametric_es(mu: float, sigma: float, level: float = 0.95) -> float:
    """Expected Shortfall (CVaR) paramétrique gaussien : perte moyenne au-delà de la VaR."""
    z = norm_ppf(1 - level)
    return -mu + sigma * norm_pdf(z) / (1 - level)


def historical_var(returns: list[float], level: float = 0.95) -> float:
    """VaR historique (empirique) : perte au quantile (1-level)."""
    if not returns:
        return 0.0
    s = sorted(returns)
    idx = max(0, int((1 - level) * len(s)) - 1)
    return -s[idx]


def expected_shortfall(returns: list[float], level: float = 0.95) -> float:
    """ES historique : moyenne des pertes au-delà de la VaR."""
    if not returns:
        return 0.0
    s = sorted(returns)
    k = max(1, int((1 - level) * len(s)))
    return -sum(s[:k]) / k


def sharpe_ratio(returns: list[float], rf: float = 0.0) -> float:
    """Ratio de Sharpe = (rendement moyen − taux sans risque) / volatilité."""
    n = len(returns)
    if n < 2:
        return 0.0
    mean = sum(returns) / n
    var = sum((x - mean) ** 2 for x in returns) / (n - 1)
    sd = var ** 0.5
    return (mean - rf) / sd if sd else 0.0


def portfolio_volatility(weights: list[float], cov: list[list[float]]) -> float:
    """Volatilité d'un portefeuille : √(wᵀ Σ w)."""
    n = len(weights)
    var = sum(weights[i] * weights[j] * cov[i][j] for i in range(n) for j in range(n))
    return math.sqrt(max(var, 0.0))


def beta(asset_returns: list[float], market_returns: list[float]) -> float:
    """Bêta = cov(actif, marché) / var(marché)."""
    n = min(len(asset_returns), len(market_returns))
    if n < 2:
        return 0.0
    ma = sum(asset_returns[:n]) / n
    mm = sum(market_returns[:n]) / n
    cov = sum((asset_returns[i] - ma) * (market_returns[i] - mm) for i in range(n)) / (n - 1)
    varm = sum((market_returns[i] - mm) ** 2 for i in range(n)) / (n - 1)
    return cov / varm if varm else 0.0


# ------------------------------------------------------------------ domaine + cas de référence
TRADING = Domain(
    name="trading",
    entity_types={
        "Option": EntityType("Option",
            {a.name: a for a in [
                _A("strike", "money", "€"), _A("maturite_ans", "metric", "ans"),
                _A("vol_implicite", "ratio"), _A("prix", "money", "€"),
                _A("delta", "ratio"), _A("gamma", "metric"), _A("vega", "metric"),
                _A("theta", "metric"), _A("rho", "metric")]},
            "Option européenne (Black-Scholes)"),
        "Asset": EntityType("Asset",
            {a.name: a for a in [_A("vol_realisee", "ratio"), _A("beta", "ratio")]},
            "Actif tradable (enrichi : vol réalisée, bêta)"),
        "Portfolio": EntityType("Portfolio",
            {a.name: a for a in [
                _A("valeur", "money", "€"), _A("volatilite", "ratio"),
                _A("var_95", "money", "€"), _A("es_95", "money", "€"), _A("sharpe", "ratio")]},
            "Portefeuille (VaR, ES, Sharpe)"),
    },
    equations={"black_scholes": black_scholes, "greeks": greeks,
               "parametric_var": parametric_var, "parametric_es": parametric_es,
               "historical_var": historical_var, "expected_shortfall": expected_shortfall,
               "sharpe_ratio": sharpe_ratio, "portfolio_volatility": portfolio_volatility, "beta": beta},
    reference_cases=[
        # valeurs de référence (manuel de finance) : S=K=100, r=5%, σ=20%, T=1
        {"equation": "black_scholes", "kwargs": {"S": 100, "K": 100, "r": 0.05, "sigma": 0.2, "T": 1},
         "expected": 10.4506, "tol": 1e-3},
        {"equation": "black_scholes", "kwargs": {"S": 100, "K": 100, "r": 0.05, "sigma": 0.2, "T": 1, "kind": "put"},
         "expected": 5.5735, "tol": 1e-3},
        {"equation": "parametric_var", "kwargs": {"mu": 0.0, "sigma": 1.0, "level": 0.95},
         "expected": 1.6449, "tol": 1e-3},
        {"equation": "parametric_es", "kwargs": {"mu": 0.0, "sigma": 1.0, "level": 0.95},
         "expected": 2.0627, "tol": 1e-3},
    ],
)
