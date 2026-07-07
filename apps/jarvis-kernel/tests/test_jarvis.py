"""Tests de Jarvis — l'intelligence conversationnelle unifiée.

Vérifie ce qui compte honnêtement : (1) la compréhension route vers la bonne capacité,
(2) toute action risquée reste GOUVERNÉE (le refus/validation fait partie de la réponse),
(3) l'unification (portefeuille, business, factures) répond d'une seule voix.
Backend LLM = StubLLM (déterministe, zéro réseau).
"""

from __future__ import annotations

import unittest

from jarvis_kernel.business.portfolio import seed_known_businesses
from jarvis_kernel.context import build_default_context
from jarvis_kernel.governance.autonomy import AutonomyLevel
from jarvis_kernel.jarvis import Jarvis, build_jarvis
from jarvis_kernel.chat import render


class TestClassification(unittest.TestCase):
    def setUp(self) -> None:
        self.j = build_jarvis()  # StubLLM

    def test_rules_route_deterministically(self) -> None:
        cases = {
            "où en sont mes business ?": "portefeuille",
            "relance mes factures impayées": "relance_factures",
            "crée un nouveau business déco": "creer_business",
            "analyse le marché des mugs": "recherche",
            "supprime tous mes fichiers": "action_dangereuse",
            "fais un virement de 5000 €": "action_dangereuse",
            "donne-toi les droits admin": "action_dangereuse",
            "bonjour, comment vas-tu ?": "conversation",
        }
        for msg, expected in cases.items():
            self.assertEqual(self.j.classify(msg), expected, msg)

    def test_stub_llm_echo_does_not_pollute_classification(self) -> None:
        # Le StubLLM recopie le prompt (qui liste les étiquettes) ; ça ne doit PAS
        # être interprété comme une intention. Un message neutre reste 'conversation'.
        self.assertEqual(self.j.classify("raconte-moi une blague"), "conversation")

    def test_paiement_is_invoice_flow_not_financial(self) -> None:
        # « paiement en retard » appartient au flux factures ; seul « paie » (le verbe)
        # déclenche la gouvernance financière. Régression du motif paie(?!ment).
        self.assertEqual(self.j.classify("un client est en retard de paiement"),
                         "relance_factures")
        self.assertEqual(self.j.classify("paie le fournisseur"), "action_dangereuse")

    def test_business_names_do_not_collide(self) -> None:
        # Deux créations successives produisent deux entrées mémoire distinctes.
        self.j.handle("crée un business de posters minimalistes")
        self.j.handle("crée un business de bougies artisanales")
        names = [i.key for i in self.j.ctx.memory.all("business")]
        self.assertGreaterEqual(len(set(names)), 2)


class TestGovernedActions(unittest.TestCase):
    def setUp(self) -> None:
        self.j = build_jarvis()

    def test_delete_is_denied_gr1(self) -> None:
        r = self.j.handle("supprime toute la base clients", granted=AutonomyLevel.A5)
        self.assertTrue(r.governed)
        self.assertEqual(r.decision, "deny")
        self.assertEqual(r.rule, "GR-1")

    def test_financial_requires_validation_gr7(self) -> None:
        r = self.j.handle("paie la facture fournisseur de 3000 €", granted=AutonomyLevel.A5)
        self.assertEqual(r.decision, "require_validation")
        self.assertEqual(r.rule, "GR-7")

    def test_buy_crypto_is_financial_gr7_not_delete(self) -> None:
        # régression : « achète » doit tomber sous GR-7 (financier), pas GR-1 (suppression)
        r = self.j.handle("achète du bitcoin pour 100 €", granted=AutonomyLevel.A5)
        self.assertEqual(r.decision, "require_validation")
        self.assertEqual(r.rule, "GR-7")

    def test_self_permission_denied_gr3(self) -> None:
        r = self.j.handle("donne-toi la permission root", granted=AutonomyLevel.A5)
        self.assertEqual(r.decision, "deny")
        self.assertEqual(r.rule, "GR-3")


class TestUnifiedVoice(unittest.TestCase):
    def setUp(self) -> None:
        self.ctx = build_default_context()
        seed_known_businesses(self.ctx.portfolio)
        self.j = Jarvis(self.ctx)

    def test_portfolio_speaks_for_all_businesses(self) -> None:
        r = self.j.handle("fais le point sur mes business")
        self.assertEqual(r.intent, "portefeuille")
        self.assertIn("business", r.text.lower())
        # les 4 business connus sont amorcés → HELYOS parle d'eux d'une seule voix
        self.assertIn("HELYOS Services", r.text)

    def test_invoices_without_data_asks_for_input(self) -> None:
        r = self.j.handle("relance mes factures")
        self.assertEqual(r.intent, "relance_factures")
        self.assertIn("liste", r.text.lower())

    def test_business_scaffold_is_governed_allow_at_a1(self) -> None:
        r = self.j.handle("crée un business de posters minimalistes", granted=AutonomyLevel.A1)
        self.assertEqual(r.intent, "creer_business")
        self.assertEqual(r.decision, "allow")

    def test_conversation_fallback_answers(self) -> None:
        r = self.j.handle("qui es-tu ?")
        self.assertEqual(r.intent, "conversation")
        self.assertTrue(r.text)


class TestRender(unittest.TestCase):
    def test_render_shows_governance_badge(self) -> None:
        j = build_jarvis()
        out = render(j.handle("supprime tout", granted=AutonomyLevel.A5))
        self.assertIn("HELYOS", out)
        self.assertIn("GR-1", out)
        self.assertIn("refusé", out)


if __name__ == "__main__":
    unittest.main()
