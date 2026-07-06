"""Tests des connecteurs (RFC-0009). Aucun réseau : transports/SMTP injectés.

Ce qui compte : (1) l'honnêteté des statuts (TradingView = interdit, non-configuré
le dit), (2) la gouvernance sur l'envoi (GR-2 : rien ne part sans validation),
(3) le sync alimente le portefeuille avec les chiffres reçus, sans invention.
"""

from __future__ import annotations

import unittest

from jarvis_kernel.business.portfolio import BusinessPortfolio, seed_known_businesses
from jarvis_kernel.config import Settings
from jarvis_kernel.connectors import build_connectors
from jarvis_kernel.connectors.github import GitHubConnector
from jarvis_kernel.connectors.shopify import ShopifyConnector
from jarvis_kernel.connectors.smtp import SMTPConnector
from jarvis_kernel.connectors.trading import TradingViewConnector
from jarvis_kernel.context import build_default_context
from jarvis_kernel.governance.autonomy import AutonomyLevel
from jarvis_kernel.memory.store import InMemoryMemoryStore


def _portfolio() -> BusinessPortfolio:
    p = BusinessPortfolio(InMemoryMemoryStore())
    seed_known_businesses(p)
    return p


class TestStatuses(unittest.TestCase):
    def test_tradingview_is_forbidden_with_reason(self) -> None:
        st = TradingViewConnector().status()
        self.assertEqual(st.status, "forbidden")
        self.assertIn("ADR-0010", st.detail)
        self.assertIn("GR-7", st.detail)

    def test_unconfigured_shopify_says_what_it_needs(self) -> None:
        st = ShopifyConnector(shop="", token="").status()
        self.assertEqual(st.status, "not_configured")
        self.assertIn("HELYOS_SHOPIFY_SHOP", st.requires)

    def test_registry_builds_all(self) -> None:
        names = {c.name for c in build_connectors(Settings())}
        self.assertTrue({"shopify", "github", "smtp", "ollama", "tradingview",
                         "stripe", "n8n", "nocodb", "youtube"} <= names)


class TestShopifySync(unittest.TestCase):
    def test_sync_writes_real_metrics_to_ecommerce_business(self) -> None:
        def transport(url: str, headers: dict) -> dict:
            self.assertIn("X-Shopify-Access-Token", headers)
            if "orders/count" in url:
                return {"count": 3}
            return {"orders": [{"total_price": "19.90"}, {"total_price": "45.00"}]}

        c = ShopifyConnector(shop="test.myshopify.com", token="shpat_x", transport=transport)
        p = _portfolio()
        summary = c.sync(p)
        self.assertEqual(summary["orders"], 3)
        self.assertAlmostEqual(summary["revenue_eur"], 64.90)
        biz = next(b for b in p.list() if b.kind == "ecommerce")
        self.assertEqual(biz.metrics["commandes"], 3)
        self.assertAlmostEqual(biz.metrics["revenue_eur"], 64.90)

    def test_unconfigured_sync_returns_none(self) -> None:
        self.assertIsNone(ShopifyConnector(shop="", token="").sync(_portfolio()))


class TestGitHubSync(unittest.TestCase):
    def test_sync_writes_stars(self) -> None:
        c = GitHubConnector(repo="x/y",
                            transport=lambda u, h: {"stargazers_count": 7, "forks_count": 2})
        p = _portfolio()
        self.assertEqual(c.sync(p)["stars"], 7)
        biz = next(b for b in p.list() if b.kind == "opensource")
        self.assertEqual(biz.metrics["stars"], 7)


class _FakeSMTP:
    sent: list = []

    def __init__(self, host, port, timeout=0):
        pass

    def starttls(self):
        pass

    def login(self, u, p):
        pass

    def send_message(self, msg):
        _FakeSMTP.sent.append(msg)

    def quit(self):
        pass


class TestSMTPGovernance(unittest.TestCase):
    def setUp(self) -> None:
        _FakeSMTP.sent = []
        self.ctx = build_default_context()
        self.smtp = SMTPConnector(host="smtp.test", port=587, user="u", password="p",
                                  sender="helyos@test.fr", smtp_factory=_FakeSMTP)

    def test_send_without_validation_is_blocked_even_at_a5(self) -> None:
        v, sent = self.smtp.send_email(self.ctx.governance, to="client@x.fr",
                                       subject="Relance", body="…",
                                       granted=AutonomyLevel.A5, validated=False)
        self.assertEqual(v.decision.value, "require_validation")
        self.assertEqual(v.rule, "GR-2")
        self.assertFalse(sent)
        self.assertEqual(_FakeSMTP.sent, [])       # RIEN n'est parti

    def test_send_with_validation_goes_out(self) -> None:
        v, sent = self.smtp.send_email(self.ctx.governance, to="client@x.fr",
                                       subject="Relance F-001", body="Bonjour…",
                                       granted=AutonomyLevel.A2, validated=True)
        self.assertTrue(v.allowed)
        self.assertTrue(sent)
        self.assertEqual(len(_FakeSMTP.sent), 1)
        self.assertEqual(_FakeSMTP.sent[0]["To"], "client@x.fr")

    def test_unconfigured_smtp_never_sends_even_validated(self) -> None:
        bare = SMTPConnector(host="", sender="", smtp_factory=_FakeSMTP)
        v, sent = bare.send_email(self.ctx.governance, to="a@b.fr", subject="s",
                                  body="b", validated=True)
        self.assertTrue(v.allowed)
        self.assertFalse(sent)                     # autorisé mais pas branché : honnête


if __name__ == "__main__":
    unittest.main()
