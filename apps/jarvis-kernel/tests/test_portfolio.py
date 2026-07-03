"""Tests du BusinessPortfolio — HELYOS gère un portefeuille de business."""

import unittest

from jarvis_kernel.business.portfolio import Business, BusinessPortfolio, seed_known_businesses
from jarvis_kernel.context import build_default_context
from jarvis_kernel.memory.store import InMemoryMemoryStore


class TestPortfolio(unittest.TestCase):
    def setUp(self):
        self.p = BusinessPortfolio(InMemoryMemoryStore())

    def test_register_get_list(self):
        self.p.register(Business(name="Boutique", kind="ecommerce"))
        self.assertEqual(self.p.get("Boutique").kind, "ecommerce")
        self.assertEqual(len(self.p.list()), 1)

    def test_status_metric_task_flow(self):
        self.p.register(Business(name="YT", kind="youtube"))
        self.p.set_status("YT", "lancée")
        self.p.set_metric("YT", "abonnes", 42)
        self.p.add_task("YT", "publier une vidéo", owner="humain")
        b = self.p.get("YT")
        self.assertEqual(b.status, "lancée")
        self.assertEqual(b.metrics["abonnes"], 42)
        self.assertEqual(b.open_tasks, 1)
        self.p.complete_task("YT", "publier")
        self.assertEqual(self.p.get("YT").open_tasks, 0)

    def test_summary(self):
        self.p.register(Business(name="A", kind="ecommerce", status="idée"))
        s = self.p.summary()
        self.assertEqual(s[0]["name"], "A")
        self.assertIn("open_tasks", s[0])

    def test_seed_four_businesses(self):
        names = seed_known_businesses(self.p)
        self.assertEqual(len(names), 4)               # Shopify = 1 sur 4
        kinds = {b.kind for b in self.p.list()}
        self.assertIn("ecommerce", kinds)
        self.assertIn("youtube", kinds)
        self.assertIn("opensource", kinds)

    def test_portfolio_in_context(self):
        ctx = build_default_context()
        self.assertIsInstance(ctx.portfolio, BusinessPortfolio)


if __name__ == "__main__":
    unittest.main()
