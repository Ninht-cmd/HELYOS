"""Tests du diagnostic CI : parsing traceback, diagnostic multi-signaux, auto-contradiction,
lecture GitHub Actions réelle (résiliente)."""

from __future__ import annotations

import unittest
from pathlib import Path

from jarvis_kernel.world.ci_diagnosis import (CIFailureFinding, diagnose,
                                              parse_unittest_failures, record_ci_outcome)
from jarvis_kernel.world.memory_store import UnifiedMemory
from jarvis_kernel.world.toolbus import GitHubConnector

ROOT = Path(__file__).resolve().parents[3]
POLICY = "apps/jarvis-kernel/src/jarvis_kernel/governance/policy.py"

_OUT = r'''
......F
======================================================================
FAIL: test_governance_external_action (tests.test_gov.TestGov.test_governance_external_action)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "C:/x/apps/jarvis-kernel/tests/test_gov.py", line 20, in test_governance_external_action
    self.assertEqual(v.decision, Decision.REQUIRE_VALIDATION)
  File "C:/x/apps/jarvis-kernel/src/jarvis_kernel/governance/policy.py", line 184, in evaluate
    return verdict(Decision.ALLOW, "simplifié")
AssertionError: <Decision.ALLOW> != <Decision.REQUIRE_VALIDATION>
----------------------------------------------------------------------
Ran 7 tests in 0.01s
FAILED (failures=1)
'''


class TestParse(unittest.TestCase):
    def test_extracts_source_frame_not_test_frame(self) -> None:
        fs = parse_unittest_failures(_OUT)
        self.assertEqual(len(fs), 1)
        f = fs[0]
        self.assertEqual(f.exception_type, "AssertionError")
        self.assertTrue(f.file.endswith("governance/policy.py"))   # le SOURCE, pas le test
        self.assertEqual(f.symbol, "evaluate")
        self.assertEqual(f.line, 184)


class TestDiagnose(unittest.TestCase):
    def test_multisignal_confidence_and_linked_decision(self) -> None:
        mem = UnifiedMemory()
        oid = mem.start_episode("x")
        d = mem.record_decision(oid, "dev_agent", "simplifier la règle GR-2",
                                entities=["evaluate", "category:complexity"])
        f = CIFailureFinding(test="test_gov", exception_type="AssertionError",
                             message="ALLOW != REQUIRE_VALIDATION", file=POLICY, line=184, symbol="evaluate")
        diagnose(f, ROOT, mem)
        self.assertIn("Régression", f.diagnosis)
        self.assertEqual(f.linked_decision, d)                     # décision liée retrouvée
        self.assertTrue(f.culprit_commit)                          # commit réel via git
        self.assertGreater(f.observation_confidence, f.diagnosis_confidence)
        self.assertGreater(f.diagnosis_confidence, f.action_confidence)

    def test_confidence_rises_with_signals(self) -> None:
        thin = diagnose(CIFailureFinding(test="t", exception_type="E", message="m", file=None), ROOT)
        rich = diagnose(CIFailureFinding(test="t", exception_type="E", message="m",
                        file=POLICY, line=1, symbol="evaluate"), ROOT)
        self.assertGreater(rich.diagnosis_confidence, thin.diagnosis_confidence)  # plus de signaux → plus sûr


class TestSelfContradiction(unittest.TestCase):
    def test_broken_ci_downgrades_prior_decision(self) -> None:
        mem = UnifiedMemory()
        oid = mem.start_episode("x")
        d = mem.record_decision(oid, "dev_agent", "changement faible risque", entities=["y"])
        record_ci_outcome(mem, oid, ci_passed=False, related_decisions=[d])
        self.assertEqual(mem.decisions[d].status, "rejected")      # la CI cassée contredit la décision


class TestGitHubActionsLive(unittest.TestCase):
    def test_reads_real_runs(self) -> None:
        r = GitHubConnector("Ninht-cmd", "HELYOS").read("runs", n=3)
        if not r.ok:
            self.skipTest(f"réseau indisponible : {r.note}")
        self.assertIsInstance(r.data, list)
        if r.data:
            self.assertIn("conclusion", r.data[0])                 # runs Actions réels lus


if __name__ == "__main__":
    unittest.main()
