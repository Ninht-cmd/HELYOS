"""Tests de l'analyste de marché (RFC-0010). Aucun réseau : transport injecté.

L'essentiel : (1) les indicateurs sont calculés juste, (2) l'analyse est gouvernée
(A1), (3) une proposition d'ordre n'est JAMAIS autonome (GR-7) et l'exécution
n'existe pas même après validation (aucun courtier branché).
"""

from __future__ import annotations

import unittest

from jarvis_kernel.agents.market_analyst import MarketAnalystAgent, rsi, sma
from jarvis_kernel.connectors.market import MarketDataConnector
from jarvis_kernel.context import build_default_context
from jarvis_kernel.governance.autonomy import AutonomyLevel


def _fake_transport(url: str, headers: dict):
    if "ticker/24hr" in url:
        return {"lastPrice": "50000.0", "priceChangePercent": "2.5"}
    # klines : 60 jours de hausse régulière -> SMA20 > SMA50, RSI élevé
    return [[0, "0", "0", "0", str(1000 + i * 10), "0"] for i in range(60)]


class TestIndicators(unittest.TestCase):
    def test_sma(self) -> None:
        self.assertEqual(sma([1, 2, 3, 4], 2), 3.5)
        self.assertIsNone(sma([1, 2], 5))          # historique insuffisant = None, pas 0

    def test_rsi_bounds(self) -> None:
        up = [float(i) for i in range(20)]          # que des hausses
        self.assertEqual(rsi(up), 100.0)
        down = [float(20 - i) for i in range(20)]   # que des baisses
        self.assertEqual(rsi(down), 0.0)
        self.assertIsNone(rsi([1.0, 2.0]))          # trop court


class TestAnalyze(unittest.TestCase):
    def setUp(self) -> None:
        self.ctx = build_default_context()
        self.agent = MarketAnalystAgent(market=MarketDataConnector(transport=_fake_transport))

    def test_analyze_is_governed_and_computes(self) -> None:
        v, briefs = self.agent.analyze(self.ctx.governance, symbols=("BTCUSDT",),
                                       granted=AutonomyLevel.A1)
        self.assertTrue(v.allowed)
        b = briefs[0]
        self.assertEqual(b.price_usdt, 50000.0)
        self.assertEqual(b.trend, "haussière")      # série croissante
        self.assertGreater(b.rsi14, 70)             # série toujours haussière
        self.assertIn("pas un conseil financier", self.agent.summary_text(briefs))

    def test_analyze_blocked_below_a1(self) -> None:
        v, briefs = self.agent.analyze(self.ctx.governance, symbols=("BTCUSDT",),
                                       granted=AutonomyLevel.A0)
        self.assertFalse(v.allowed)
        self.assertEqual(briefs, [])


class TestTradeProposalGovernance(unittest.TestCase):
    def setUp(self) -> None:
        self.ctx = build_default_context()
        self.agent = MarketAnalystAgent(market=MarketDataConnector(transport=_fake_transport))

    def test_trade_requires_validation_even_at_a5(self) -> None:
        v, order = self.agent.propose_trade(self.ctx.governance, symbol="BTCUSDT",
                                            side="achat", amount_eur=100.0,
                                            granted=AutonomyLevel.A5, validated=False)
        self.assertEqual(v.decision.value, "require_validation")
        self.assertEqual(v.rule, "GR-7")
        self.assertFalse(order["executed"])

    def test_even_validated_nothing_executes(self) -> None:
        # validée -> autorisée, mais AUCUN courtier : executed reste False, et on dit pourquoi
        v, order = self.agent.propose_trade(self.ctx.governance, symbol="BTCUSDT",
                                            side="achat", amount_eur=100.0,
                                            granted=AutonomyLevel.A5, validated=True)
        self.assertTrue(v.allowed)
        self.assertFalse(order["executed"])
        self.assertIn("courtier", order["reason"])


class TestJarvisRouting(unittest.TestCase):
    def test_market_intent_routes(self) -> None:
        from jarvis_kernel.jarvis import build_jarvis
        j = build_jarvis()
        self.assertEqual(j.classify("analyse le marché crypto"), "marche_financier")
        self.assertEqual(j.classify("quel est le cours du bitcoin ?"), "marche_financier")
        self.assertEqual(j.classify("achète du bitcoin"), "action_dangereuse")  # GR-7 d'abord


if __name__ == "__main__":
    unittest.main()
