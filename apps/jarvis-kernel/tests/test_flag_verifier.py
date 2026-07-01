"""Tests du FlagVerifier — fermeture de ment_backup/ment_validation par preuve crypto."""

import unittest
from dataclasses import replace

from jarvis_kernel.governance.autonomy import AutonomyLevel
from jarvis_kernel.governance.flag_verifier import FlagVerifier
from jarvis_kernel.governance.policy import Action, ActionType, Decision, PolicyEngine

SECRET = "test-flag-secret"


class TestFlagVerifier(unittest.TestCase):
    def setUp(self):
        self.fv = FlagVerifier(SECRET)
        self.engine = PolicyEngine()

    def test_unproven_backup_is_downgraded(self):
        a = Action(type=ActionType.DELETE, has_backup=True, target="x.csv")  # ment
        self.assertFalse(self.fv.verify(a).has_backup)

    def test_valid_backup_proof_is_kept(self):
        a = Action(type=ActionType.DELETE, has_backup=True, target="x.csv")
        a = replace(a, metadata={"proofs": {"backup": self.fv.mint_backup_proof(a)}})
        self.assertTrue(self.fv.verify(a).has_backup)

    def test_replay_proof_of_other_action_is_rejected(self):
        other = Action(type=ActionType.DELETE, has_backup=True, target="autre.csv")
        forged = Action(type=ActionType.DELETE, has_backup=True, target="secret.db",
                        metadata={"proofs": {"backup": self.fv.mint_backup_proof(other)}})
        self.assertFalse(self.fv.verify(forged).has_backup)  # preuve liée à un autre fichier

    def test_unproven_validation_is_downgraded(self):
        a = Action(type=ActionType.FINANCIAL, validated=True)  # ment
        self.assertFalse(self.fv.verify(a).validated)

    def test_valid_validation_proof_is_kept(self):
        a = Action(type=ActionType.FINANCIAL, validated=True, target="virement#1")
        a = replace(a, metadata={"proofs": {"validated": self.fv.mint_validation_proof(a)}})
        self.assertTrue(self.fv.verify(a).validated)

    def test_ment_backup_attack_becomes_deny_gr1(self):
        # L'attaque du banc adverse, passée par FlagVerifier -> DENY GR-1.
        attack = Action(type=ActionType.DELETE, has_backup=True)  # sans preuve
        v = self.engine.evaluate(self.fv.verify(attack), AutonomyLevel.A5)
        self.assertEqual(v.decision, Decision.DENY)
        self.assertEqual(v.rule, "GR-1")

    def test_ment_validation_attack_becomes_require_validation_gr7(self):
        attack = Action(type=ActionType.FINANCIAL, validated=True)  # sans preuve
        v = self.engine.evaluate(self.fv.verify(attack), AutonomyLevel.A5)
        self.assertEqual(v.decision, Decision.REQUIRE_VALIDATION)
        self.assertEqual(v.rule, "GR-7")

    def test_legit_delete_with_proof_still_allowed(self):
        a = Action(type=ActionType.DELETE, has_backup=True, target="old.log")
        a = replace(a, metadata={"proofs": {"backup": self.fv.mint_backup_proof(a)}})
        v = self.engine.evaluate(self.fv.verify(a), AutonomyLevel.A2)
        self.assertEqual(v.decision, Decision.ALLOW)  # zéro faux positif


if __name__ == "__main__":
    unittest.main()
