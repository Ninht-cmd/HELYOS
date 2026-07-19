"""Tests du Comité C-suite (mapping du PROMPT MASTER, en conseillers gouvernés)."""

from __future__ import annotations

import unittest

from jarvis_kernel.agents.advisory import ROLES, AdvisoryBoard
from jarvis_kernel.context import build_default_context
from jarvis_kernel.governance.autonomy import AutonomyLevel


class TestAdvisory(unittest.TestCase):
    def setUp(self) -> None:
        self.ctx = build_default_context()

    def test_twelve_roles_present(self) -> None:
        self.assertGreaterEqual(len(ROLES), 12)
        for k in ("ceo", "cfo", "cto", "cmo", "sales", "legal", "ciso", "data"):
            self.assertIn(k, ROLES)

    def test_role_routing_by_name_and_alias(self) -> None:
        pick = AdvisoryBoard.pick_role
        self.assertEqual(pick("demande au CFO ce qu'il pense").key, "cfo")
        self.assertEqual(pick("avis du directeur juridique").key, "legal")
        self.assertEqual(pick("côté sécurité, on en est où").key, "ciso")
        self.assertIsNone(pick("une question générale sans rôle"))   # -> CEO par défaut

    def test_advice_is_governed_and_grounded(self) -> None:
        board = AdvisoryBoard(llm=self.ctx.llm)
        v, out = board.advise(self.ctx, self.ctx.governance, "que dit le CFO sur ma trésorerie ?")
        self.assertTrue(v.allowed)
        self.assertEqual(out["role"], "cfo")
        # l'analyse est bien passée par la gouvernance (tracée dans l'audit)
        self.assertGreater(len(self.ctx.governance.audit), 0)

    def test_advice_blocked_below_a1(self) -> None:
        v, out = AdvisoryBoard(llm=self.ctx.llm).advise(
            self.ctx, self.ctx.governance, "conseil du CEO", granted=AutonomyLevel.A0)
        self.assertFalse(v.allowed)
        self.assertIsNone(out)

    def test_advisor_never_executes(self) -> None:
        # un conseiller ne produit qu'une action ANALYZE — jamais FINANCIAL/EXTERNAL
        board = AdvisoryBoard(llm=self.ctx.llm)
        board.advise(self.ctx, self.ctx.governance, "le CFO doit-il faire un virement ?")
        types = [e.action_type for e in self.ctx.governance.audit.tail(10)]
        self.assertIn("analyze", types)
        self.assertNotIn("financial", types)

    def test_jarvis_routes_conseil(self) -> None:
        j = self.ctx.jarvis
        self.assertEqual(j.classify("demande au CFO"), "conseil")
        self.assertEqual(j.classify("avis du comité sur ma stratégie"), "conseil")
        # « fais un virement » reste dangereux, pas un conseil
        self.assertEqual(j.classify("fais un virement de 500 €"), "action_dangereuse")
        # régression : « acheteurs » (nom) ne doit PAS déclencher la règle financière
        self.assertEqual(j.classify("CMO, comment faire venir des acheteurs ?"), "conseil")
        # mais « achète du bitcoin » (verbe) reste bien dangereux
        self.assertEqual(j.classify("achète du bitcoin pour 100 €"), "action_dangereuse")


if __name__ == "__main__":
    unittest.main()
