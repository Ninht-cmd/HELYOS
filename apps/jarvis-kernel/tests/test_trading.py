"""Tests du domaine Trading : équations quant vérifiées contre des valeurs de référence
(manuel de finance), + le harnais de validation de domaine."""

from __future__ import annotations

import unittest

from jarvis_kernel.world.domains import validate_domain
from jarvis_kernel.world.domains.trading import (TRADING, beta, black_scholes,
                                                 expected_shortfall, greeks,
                                                 historical_var, norm_cdf, norm_ppf,
                                                 parametric_es, parametric_var,
                                                 portfolio_volatility, sharpe_ratio)


class TestGaussian(unittest.TestCase):
    def test_cdf_and_ppf(self) -> None:
        self.assertAlmostEqual(norm_cdf(0.0), 0.5, places=6)
        self.assertAlmostEqual(norm_cdf(1.96), 0.975, places=3)
        self.assertAlmostEqual(norm_ppf(0.975), 1.96, places=2)      # inverse cohérent


class TestBlackScholes(unittest.TestCase):
    # Cas manuel : S=K=100, r=5%, σ=20%, T=1
    P = dict(S=100, K=100, r=0.05, sigma=0.2, T=1)

    def test_call_and_put_prices(self) -> None:
        self.assertAlmostEqual(black_scholes(**self.P, kind="call"), 10.4506, places=3)
        self.assertAlmostEqual(black_scholes(**self.P, kind="put"), 5.5735, places=3)

    def test_put_call_parity(self) -> None:
        import math
        c = black_scholes(**self.P, kind="call")
        p = black_scholes(**self.P, kind="put")
        # C - P = S - K e^{-rT}
        self.assertAlmostEqual(c - p, 100 - 100 * math.exp(-0.05), places=6)

    def test_greeks_reference(self) -> None:
        g = greeks(**self.P, kind="call")
        self.assertAlmostEqual(g["delta"], 0.6368, places=3)
        self.assertAlmostEqual(g["gamma"], 0.018762, places=4)
        self.assertAlmostEqual(g["vega"], 37.524, places=2)
        self.assertAlmostEqual(g["rho"], 53.232, places=2)
        self.assertLess(g["theta"], 0)                               # long call : theta négatif


class TestRisk(unittest.TestCase):
    def test_parametric_var_es_normal(self) -> None:
        self.assertAlmostEqual(parametric_var(0.0, 1.0, 0.95), 1.6449, places=3)
        self.assertAlmostEqual(parametric_es(0.0, 1.0, 0.95), 2.0627, places=3)

    def test_historical_var_es_monotone(self) -> None:
        rets = [(-5 + i) / 100 for i in range(11)]                   # -5%..+5%
        var = historical_var(rets, 0.8)                              # queue = 2 points
        es = expected_shortfall(rets, 0.8)
        self.assertGreater(es, var)                                  # ES > VaR (perte moyenne pire)

    def test_sharpe_and_beta(self) -> None:
        rets = [0.01, 0.02, -0.01, 0.03, 0.00]
        self.assertGreater(sharpe_ratio(rets, rf=0.0), 0)
        mkt = [0.01, 0.02, -0.01, 0.03, 0.00]
        self.assertAlmostEqual(beta(rets, mkt), 1.0, places=6)       # actif = marché -> bêta 1

    def test_portfolio_volatility(self) -> None:
        # 2 actifs σ=0.2 chacun, corrélation 0 -> vol = 0.2/√2 pour poids égaux
        cov = [[0.04, 0.0], [0.0, 0.04]]
        self.assertAlmostEqual(portfolio_volatility([0.5, 0.5], cov), 0.2 / (2 ** 0.5), places=6)


class TestDomainValidation(unittest.TestCase):
    def test_reference_cases_pass(self) -> None:
        r = validate_domain(TRADING)
        self.assertEqual(r["passes"], r["total"])                    # toutes les lois validées
        self.assertGreaterEqual(r["total"], 4)


if __name__ == "__main__":
    unittest.main()
