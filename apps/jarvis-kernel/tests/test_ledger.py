"""Tests du livre de caisse (RFC-0014) — le CA affiché devient une somme vérifiable."""

from __future__ import annotations

import time
import unittest

from jarvis_kernel.business.ledger import Ledger
from jarvis_kernel.business.portfolio import seed_known_businesses
from jarvis_kernel.context import build_default_context
from jarvis_kernel.governance.autonomy import AutonomyLevel


class TestLedger(unittest.TestCase):
    def setUp(self) -> None:
        self.ctx = build_default_context()
        seed_known_businesses(self.ctx.portfolio)
        self.svc = "HELYOS Services (automatisation admin)"

    def test_math_is_honest(self) -> None:
        led: Ledger = self.ctx.ledger
        led.add(self.svc, "recette", 350, "pilote agence X")
        led.add(self.svc, "depense", 20.5, "VPS")
        s = led.summary(self.svc)
        self.assertEqual((s["recettes_eur"], s["depenses_eur"], s["solde_eur"]),
                         (350.0, 20.5, 329.5))

    def test_revenue_metric_is_now_the_sum_of_entries(self) -> None:
        # le CA affiché sur le board/portefeuille = la somme des écritures, pas un chiffre posé
        self.ctx.ledger.add(self.svc, "recette", 350, "pilote")
        b = self.ctx.portfolio.get(self.svc)
        self.assertEqual(b.metrics["revenue_eur"], 350.0)
        self.assertEqual(b.metrics["solde_eur"], 350.0)

    def test_rejects_garbage(self) -> None:
        with self.assertRaises(ValueError):
            self.ctx.ledger.add(self.svc, "loterie", 10)
        with self.assertRaises(ValueError):
            self.ctx.ledger.add(self.svc, "recette", -5)

    def test_global_summary_spans_businesses(self) -> None:
        self.ctx.ledger.add(self.svc, "recette", 100)
        self.ctx.ledger.add("Atelier Compagnon (boutique)", "depense", 30)
        g = self.ctx.ledger.global_summary()
        self.assertEqual(g["solde_eur"], 70.0)
        self.assertEqual(len(g["par_business"]), 2)


class TestJarvisTreasury(unittest.TestCase):
    def setUp(self) -> None:
        self.ctx = build_default_context()
        seed_known_businesses(self.ctx.portfolio)

    def test_encaisse_routes_parses_and_records(self) -> None:
        r = self.ctx.jarvis.handle("encaisse 350 € du pilote agence pour les services")
        self.assertEqual(r.intent, "tresorerie")
        self.assertIn("350.00", r.text)
        self.assertIn("Caisse de la holding : 350.00 €", r.text)

    def test_french_thousands_are_parsed(self) -> None:
        # régression : « 1 350 € » (espace de milliers) doit donner 1350, pas 1
        r = self.ctx.jarvis.handle("encaisse 1 350 € du pack pour les services")
        self.assertIn("1350.00", r.text)

    def test_depense_and_bilan(self) -> None:
        self.ctx.jarvis.handle("encaisse 350 € — services")
        self.ctx.jarvis.handle("dépense 20 € de VPS pour les services")
        r = self.ctx.jarvis.handle("bilan de trésorerie")
        self.assertIn("330.00", r.text)

    def test_unmatched_business_asks_instead_of_guessing(self) -> None:
        r = self.ctx.jarvis.handle("encaisse 100 €")
        self.assertIn("Pour quel business", r.text)
        self.assertEqual(self.ctx.ledger.global_summary()["par_business"], [])

    def test_virement_still_gr7_not_bookkeeping(self) -> None:
        r = self.ctx.jarvis.handle("fais un virement de 500 €", granted=AutonomyLevel.A5)
        self.assertEqual(r.rule, "GR-7")           # exécuter ≠ noter


class TestDeadlines(unittest.TestCase):
    def test_due_tasks_and_pulse_urgency(self) -> None:
        ctx = build_default_context()
        ctx.connectors = []
        soon = time.strftime("%Y-%m-%d", time.localtime(time.time() + 2 * 86400))
        far = time.strftime("%Y-%m-%d", time.localtime(time.time() + 40 * 86400))
        from jarvis_kernel.business.portfolio import Business
        ctx.portfolio.register(Business(name="Svc", kind="service"))
        ctx.portfolio.add_task("Svc", "[HUMAIN] Déclaration URSSAF", due=soon)
        ctx.portfolio.add_task("Svc", "[HUMAIN] Renouveler domaine", due=far)
        due = ctx.portfolio.due_tasks(within_days=7)
        self.assertEqual(len(due), 1)
        self.assertIn("URSSAF", ctx.pulse.briefing())


if __name__ == "__main__":
    unittest.main()
