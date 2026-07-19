"""Tests du carnet de commandes (ventes à livrer + achats fournisseurs)."""

from __future__ import annotations

import unittest

from jarvis_kernel.business.orders import OrderBook
from jarvis_kernel.context import build_default_context


class TestOrders(unittest.TestCase):
    def setUp(self) -> None:
        self.ctx = build_default_context()
        self.book = OrderBook(self.ctx.memory)

    def test_vente_lifecycle(self) -> None:
        o = self.book.add("vente", "Dupont", "pack pilote", 350)
        self.assertEqual(o.statut, "recue")
        self.assertEqual(len(self.book.to_deliver()), 1)      # à livrer
        self.book.set_statut(o.id, "livree")
        self.assertEqual(len(self.book.to_deliver()), 0)
        self.assertEqual(len(self.book.to_collect()), 1)      # à encaisser
        s = self.book.summary()
        self.assertEqual(s["a_encaisser_eur"], 350.0)

    def test_achat_and_suppliers(self) -> None:
        self.book.add("achat", "Printful", "mugs", 40)
        self.book.add("achat", "OVH", "VPS", 12)
        self.assertEqual(self.book.suppliers(), ["OVH", "Printful"])
        self.book.set_statut(self.book.list("achat")[0].id, "recue")
        self.assertEqual(len(self.book.to_pay()), 1)          # reçu, pas payé

    def test_invalid_status_rejected(self) -> None:
        o = self.book.add("vente", "X", "y", 10)
        with self.assertRaises(ValueError):
            self.book.set_statut(o.id, "payee")               # 'payee' est un statut d'achat
        with self.assertRaises(KeyError):
            self.book.set_statut("zzzz", "livree")

    def test_jarvis_add_and_route(self) -> None:
        j = self.ctx.jarvis
        self.assertEqual(j.classify("mes commandes"), "commandes")
        self.assertEqual(j.classify("achat : Printful, mugs, 40"), "commandes")
        r = j.handle("commande : client Dupont, pack pilote, 350")
        self.assertEqual(r.intent, "commandes")
        self.assertIn("Dupont", r.text)
        self.assertEqual(len(self.book.list("vente")), 1)
        self.assertEqual(self.book.list("vente")[0].montant_eur, 350.0)

    def test_pulse_flags_orders_to_deliver(self) -> None:
        self.ctx.connectors = []
        self.book.add("vente", "Dupont", "pack", 350)
        self.assertIn("à livrer", self.ctx.pulse.briefing())


if __name__ == "__main__":
    unittest.main()
