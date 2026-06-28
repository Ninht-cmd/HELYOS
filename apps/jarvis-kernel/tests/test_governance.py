"""Tests de gouvernance — les règles d'or doivent être EXÉCUTÉES, pas seulement écrites.

Chaque test est le miroir d'une ligne de CODEX/03_GOUVERNANCE. Si un test casse,
c'est soit le code, soit le Codex qui a bougé : les deux doivent rester alignés.
"""

import unittest

from jarvis_kernel.governance.autonomy import AutonomyLevel
from jarvis_kernel.governance.policy import (
    Action,
    ActionType,
    Decision,
    PolicyEngine,
)


class TestAutonomyLevel(unittest.TestCase):
    def test_ordering(self):
        self.assertGreater(AutonomyLevel.A3, AutonomyLevel.A1)
        self.assertGreaterEqual(AutonomyLevel.A2, AutonomyLevel.A2)

    def test_from_name(self):
        self.assertEqual(AutonomyLevel.from_name("A2"), AutonomyLevel.A2)
        self.assertEqual(AutonomyLevel.from_name("4"), AutonomyLevel.A4)
        # défaut sûr : jamais A5 par défaut
        self.assertEqual(AutonomyLevel.from_name("bogus"), AutonomyLevel.A1)
        self.assertEqual(AutonomyLevel.from_name(""), AutonomyLevel.A1)


class TestPolicyLevels(unittest.TestCase):
    def setUp(self):
        self.engine = PolicyEngine()

    def test_read_allowed_at_a0(self):
        v = self.engine.evaluate(Action(type=ActionType.READ), AutonomyLevel.A0)
        self.assertEqual(v.decision, Decision.ALLOW)

    def test_analyze_requires_a1(self):
        a = Action(type=ActionType.ANALYZE)
        self.assertEqual(self.engine.evaluate(a, AutonomyLevel.A0).decision,
                         Decision.REQUIRE_VALIDATION)
        self.assertEqual(self.engine.evaluate(a, AutonomyLevel.A1).decision,
                         Decision.ALLOW)

    def test_write_local_requires_a2(self):
        a = Action(type=ActionType.WRITE_LOCAL, description="écrire un fichier")
        self.assertEqual(self.engine.evaluate(a, AutonomyLevel.A1).decision,
                         Decision.REQUIRE_VALIDATION)
        self.assertEqual(self.engine.evaluate(a, AutonomyLevel.A2).decision,
                         Decision.ALLOW)

    def test_rename_workdir_is_a3(self):
        a = Action(type=ActionType.RENAME_WORKDIR, reversible=True)
        self.assertEqual(self.engine.evaluate(a, AutonomyLevel.A2).decision,
                         Decision.REQUIRE_VALIDATION)
        self.assertEqual(self.engine.evaluate(a, AutonomyLevel.A3).decision,
                         Decision.ALLOW)


class TestGoldenRules(unittest.TestCase):
    def setUp(self):
        self.engine = PolicyEngine()

    def test_gr1_delete_without_backup_is_denied(self):
        """GR-1 : jamais de suppression sans sauvegarde — DENY même à A5."""
        a = Action(type=ActionType.DELETE, has_backup=False)
        v = self.engine.evaluate(a, AutonomyLevel.A5)
        self.assertEqual(v.decision, Decision.DENY)
        self.assertEqual(v.rule, "GR-1")

    def test_gr1_delete_with_backup_follows_level(self):
        a = Action(type=ActionType.DELETE, has_backup=True)
        # Avec sauvegarde, l'action redevient une A2 normale.
        self.assertEqual(self.engine.evaluate(a, AutonomyLevel.A1).decision,
                         Decision.REQUIRE_VALIDATION)
        self.assertEqual(self.engine.evaluate(a, AutonomyLevel.A2).decision,
                         Decision.ALLOW)

    def test_gr3_self_escalation_is_denied(self):
        """GR-3 : pas d'auto-escalade — DENY même à A5."""
        a = Action(type=ActionType.SELF_PERMISSION, actor="agent.x")
        v = self.engine.evaluate(a, AutonomyLevel.A5)
        self.assertEqual(v.decision, Decision.DENY)
        self.assertEqual(v.rule, "GR-3")

    def test_gr7_financial_never_autonomous(self):
        """GR-7 : finance jamais autonome — validation requise même à A5."""
        a = Action(type=ActionType.FINANCIAL, description="virement")
        v = self.engine.evaluate(a, AutonomyLevel.A5)
        self.assertEqual(v.decision, Decision.REQUIRE_VALIDATION)
        self.assertEqual(v.rule, "GR-7")

    def test_gr7_financial_allowed_when_validated(self):
        a = Action(type=ActionType.FINANCIAL, validated=True)
        v = self.engine.evaluate(a, AutonomyLevel.A2)
        self.assertEqual(v.decision, Decision.ALLOW)

    def test_gr2_external_sensitive_requires_validation(self):
        """GR-2 : action externe sensible -> validation, même à haut niveau."""
        a = Action(type=ActionType.EXTERNAL_SENSITIVE, description="poster en ligne")
        v = self.engine.evaluate(a, AutonomyLevel.A4)
        self.assertEqual(v.decision, Decision.REQUIRE_VALIDATION)
        self.assertEqual(v.rule, "GR-2")

    def test_gr2_external_allowed_when_validated_and_level_ok(self):
        a = Action(type=ActionType.EXTERNAL_SENSITIVE, validated=True)
        self.assertEqual(self.engine.evaluate(a, AutonomyLevel.A2).decision,
                         Decision.ALLOW)

    def test_sensitive_flag_triggers_gr2_on_any_action(self):
        # Une écriture marquée sensible passe aussi par GR-2.
        a = Action(type=ActionType.WRITE_LOCAL, sensitive=True)
        v = self.engine.evaluate(a, AutonomyLevel.A2)
        self.assertEqual(v.decision, Decision.REQUIRE_VALIDATION)
        self.assertEqual(v.rule, "GR-2")


if __name__ == "__main__":
    unittest.main()
