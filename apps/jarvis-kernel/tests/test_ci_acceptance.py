"""Test d'acceptation CI de bout en bout (déterministe et permanent).

Le scénario que le Conservateur a fixé :

  1. provoquer une PANNE CI déterministe,
  2. laisser HELYOS la DIAGNOSTIQUER (chaîne causale multi-signaux, frame SOURCE),
  3. proposer le CORRECTIF sous GR-2 (REQUIRE_VALIDATION — jamais autonome),
  4. vérifier que le RETOUR AU VERT produit un Outcome qui RECALIBRE le dev_agent.

Tout est isolé dans un arbre « canary » temporaire (layout apps/jarvis-kernel/{src,tests}
attendu par run_local_ci) : aucun fichier réel n'est touché, aucune dépendance réseau ni
horloge — donc reproductible à l'identique.

La recalibration est vérifiée par des NOMBRES, pas par une intention :
  calibration = bayesian_reliability(confirmés, rejetés) = (c+2)/(c+r+4).
  CI rouge -> décision rejetée -> c=0,r=1 -> 0.40  (baisse depuis 0.50)
  retour vert -> décision confirmée -> c=1,r=1 -> 0.50  (remonte depuis 0.40)
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from jarvis_kernel.governance.autonomy import AutonomyLevel
from jarvis_kernel.governance.policy import Action, ActionType, Decision
from jarvis_kernel.governance.service import GovernanceService
from jarvis_kernel.world.ci_diagnosis import diagnose, record_ci_outcome, run_local_ci
from jarvis_kernel.world.confidence import agent_calibration
from jarvis_kernel.world.memory_store import UnifiedMemory

# --- code « canary » : la panne est levée DANS le source (pas dans le test) ---
_BUGGY = '''\
def gr2_required(action):
    """True si l'action externe sensible exige une validation (GR-2)."""
    return action.is_externl  # BUG : faute de frappe -> AttributeError dans le SOURCE
'''

_FIXED = '''\
def gr2_required(action):
    """True si l'action externe sensible exige une validation (GR-2)."""
    return action.is_external
'''

_TEST = '''\
import unittest

from canary import gr2_required


class _Action:
    is_external = True


class TestGr2(unittest.TestCase):
    def test_external_action_requires_validation(self):
        self.assertTrue(gr2_required(_Action()))

    def test_sanity(self):
        self.assertTrue(True)


if __name__ == "__main__":
    unittest.main()
'''


def _canary_tree(root: Path, source: str) -> Path:
    src = root / "apps" / "jarvis-kernel" / "src"
    tests = root / "apps" / "jarvis-kernel" / "tests"
    src.mkdir(parents=True, exist_ok=True)
    tests.mkdir(parents=True, exist_ok=True)
    (src / "canary.py").write_text(source, encoding="utf-8")
    (tests / "test_canary.py").write_text(_TEST, encoding="utf-8")
    return root


class TestCIAcceptance(unittest.TestCase):
    def test_break_diagnose_gr2_green_recalibrates_dev_agent(self) -> None:
        gov = GovernanceService()
        mem = UnifiedMemory()
        oid = mem.start_episode("simplifier la validation GR-2 (canary)")

        # Le dev_agent prend une décision « faible risque » — qui va casser la CI.
        d1 = mem.record_decision(oid, "dev_agent", "simplifier gr2_required",
                                 entities=["gr2_required", "category:complexity"])
        cal_before = agent_calibration(mem, "dev_agent")

        with tempfile.TemporaryDirectory() as td:
            root = _canary_tree(Path(td), _BUGGY)

            # 1. PANNE CI déterministe (sous-processus réel, comme la CI distante).
            run_red, failures = run_local_ci(root, pattern="test_*.py")
            self.assertEqual(run_red.conclusion, "failure")
            self.assertGreaterEqual(len(failures), 1)

            # 2. DIAGNOSTIC : frame SOURCE (pas le test), décision liée, confiance multi-signaux.
            f = failures[0]
            self.assertEqual(f.symbol, "gr2_required")            # le SOURCE, pas test_canary
            self.assertEqual(f.exception_type, "AttributeError")
            diagnose(f, root, mem)
            self.assertEqual(f.linked_decision, d1)               # relie la décision dev_agent
            self.assertGreater(f.diagnosis_confidence, 0.55)      # plus d'un signal en accord
            self.assertGreater(f.observation_confidence, f.action_confidence)  # 3 niveaux distincts

            # 3. Le CORRECTIF proposé est GOUVERNÉ : GR-2 REQUIRE_VALIDATION (jamais autonome).
            v = gov.submit(Action(type=ActionType.EXTERNAL_SENSITIVE, actor="dev_agent",
                                  description=f.recommendation, sensitive=True), AutonomyLevel.A2)
            self.assertEqual(v.decision, Decision.REQUIRE_VALIDATION)
            self.assertEqual(v.rule, "GR-2")

            # 4. La CI cassée CONTREDIT la décision -> le dev_agent redescend.
            record_ci_outcome(mem, oid, ci_passed=False, related_decisions=[d1])
            cal_after_break = agent_calibration(mem, "dev_agent")
            self.assertLess(cal_after_break, cal_before)

            # 5. Correction appliquée -> RETOUR AU VERT (même sous-processus réel).
            _canary_tree(root, _FIXED)
            run_green, _ = run_local_ci(root, pattern="test_*.py")
            self.assertEqual(run_green.conclusion, "success")
            self.assertEqual(run_green.tests_failed, 0)

            # 6. Le retour au vert produit un Outcome qui RECALIBRE le dev_agent VERS LE HAUT.
            d2 = mem.record_decision(oid, "dev_agent",
                                     "restaurer gr2_required + test de non-régression",
                                     entities=["gr2_required"])
            record_ci_outcome(mem, oid, ci_passed=True, related_decisions=[d2])
            cal_after_green = agent_calibration(mem, "dev_agent")
            self.assertGreater(cal_after_green, cal_after_break)  # la recalibration à la hausse


if __name__ == "__main__":
    unittest.main()
