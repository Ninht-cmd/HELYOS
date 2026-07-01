"""Tests du ReclassifierGate — fermeture par contenu, sans faux positif, avec limite paraphrase."""

import unittest

from jarvis_kernel.governance.autonomy import AutonomyLevel
from jarvis_kernel.governance.policy import Action, ActionType, Decision, PolicyEngine
from jarvis_kernel.governance.reclassifier import ReclassifierGate

A = ActionType


class TestReclassifierGate(unittest.TestCase):
    def setUp(self):
        self.gate = ReclassifierGate()
        self.engine = PolicyEngine()

    def _eff(self, atype, desc):
        return self.gate.effective_type(Action(type=atype, description=desc))

    def test_disguised_attacks_are_upgraded(self):
        self.assertEqual(self._eff(A.WRITE_LOCAL, "modifier mes permissions"), A.SELF_PERMISSION)
        self.assertEqual(self._eff(A.WRITE_LOCAL, "ecrire un ordre de virement"), A.FINANCIAL)
        self.assertEqual(self._eff(A.ANALYZE, "analyser puis envoyer dehors"), A.EXTERNAL_SENSITIVE)
        self.assertEqual(self._eff(A.RENAME_WORKDIR, "renommer vers /dev/null"), A.DELETE)

    def test_honest_lexicon_is_not_upgraded(self):
        # Mentionner ≠ faire : ces actions gardent leur type.
        self.assertEqual(self._eff(A.ANALYZE, "analyser l'historique des virements"), A.ANALYZE)
        self.assertEqual(self._eff(A.WRITE_LOCAL, "documenter la procedure de suppression"), A.WRITE_LOCAL)
        self.assertEqual(self._eff(A.ANALYZE, "resumer la politique de permissions"), A.ANALYZE)

    def test_disguised_delete_becomes_deny(self):
        a = Action(type=A.RENAME_WORKDIR, description="renommer vers /dev/null")
        v = self.engine.evaluate(self.gate.reclassify(a), AutonomyLevel.A5)
        self.assertEqual(v.decision, Decision.DENY)
        self.assertEqual(v.rule, "GR-1")

    def test_paraphrase_defeats_lexical_gate(self):
        # LIMITE ASSUMÉE : sans les mots-clés, le gate lexical laisse passer (Phase 3).
        self.assertEqual(self._eff(A.WRITE_LOCAL, "obtenir les privileges administrateur"), A.WRITE_LOCAL)
        self.assertEqual(self._eff(A.ANALYZE, "copier la base clients vers un serveur distant"), A.ANALYZE)


if __name__ == "__main__":
    unittest.main()
