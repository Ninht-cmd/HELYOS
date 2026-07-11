"""Tests du trading simulé (RFC-0013). Aucun réseau, aucun euro réel — jamais.

Vérités à protéger :
1. Le PaperTrader ne produit JAMAIS une action FINANCIAL (aucun ordre réel).
2. Le P&L est arithmétiquement honnête et l'étiquette SIMULATION est partout.
3. Signaux : série haussière -> achat virtuel ; retournement -> vente virtuelle.
"""

from __future__ import annotations

import unittest

from jarvis_kernel.agents.paper_trader import START_CASH, PaperTrader
from jarvis_kernel.connectors.market import MarketDataConnector
from jarvis_kernel.context import build_default_context
from jarvis_kernel.governance.autonomy import AutonomyLevel


def _rising(url: str, headers: dict):
    # hausse AVEC respirations (sinon RSI=100 = suracheté et la garde refuse d'acheter)
    return [[0, "0", "0", "0", str(1000 + i * 10 - (i % 2) * 30), "0"] for i in range(60)]


def _falling(url: str, headers: dict):
    return [[0, "0", "0", "0", str(2000 - i * 10), "0"] for i in range(60)]


def _trader(transport):
    return PaperTrader(market=MarketDataConnector(transport=transport))


class TestPaperTrader(unittest.TestCase):
    def setUp(self) -> None:
        self.ctx = build_default_context()

    def test_rising_market_buys_virtually(self) -> None:
        v, s = _trader(_rising).step(self.ctx.governance, self.ctx.memory,
                                     symbols=("BTCUSDT",))
        self.assertTrue(v.allowed)
        self.assertEqual(s["executed"], 1)
        self.assertIn("BTCUSDT", s["positions"])
        self.assertAlmostEqual(s["cash_eur"], START_CASH * 0.9, places=2)
        self.assertAlmostEqual(s["equity_eur"], START_CASH, places=2)  # acheté au prix courant
        self.assertIn("SIMULATION", s["label"])

    def test_reversal_sells_and_pnl_is_honest(self) -> None:
        t = _trader(_rising)
        t.step(self.ctx.governance, self.ctx.memory, symbols=("BTCUSDT",))
        t.market.transport = _falling                      # le marché se retourne
        v, s = t.step(self.ctx.governance, self.ctx.memory, symbols=("BTCUSDT",))
        self.assertEqual(s["positions"], {})               # position soldée
        # acheté ~1590, revendu ~1410 : la perte DOIT se voir (pas de complaisance)
        self.assertLess(s["equity_eur"], START_CASH)
        self.assertLess(s["pnl_pct"], 0)

    def test_never_emits_financial_action(self) -> None:
        _trader(_rising).step(self.ctx.governance, self.ctx.memory, symbols=("BTCUSDT",))
        types = [e.action_type for e in self.ctx.governance.audit.tail(50)]
        self.assertNotIn("financial", types)               # fictif ≠ GR-7, et surtout : rien de réel

    def test_blocked_below_a1(self) -> None:
        v, s = _trader(_rising).step(self.ctx.governance, self.ctx.memory,
                                     granted=AutonomyLevel.A0)
        self.assertFalse(v.allowed)
        self.assertIsNone(s)

    def test_jarvis_routes_simulation_but_real_orders_stay_gr7(self) -> None:
        j = self.ctx.jarvis
        self.assertEqual(j.classify("lance la simulation de trading"), "simulation_trading")
        self.assertEqual(j.classify("investis 100 € en bourse"), "action_dangereuse")


if __name__ == "__main__":
    unittest.main()
