"""Diff coverage : couverture des lignes MODIFIÉES par une décision HELYOS.

- Unitaires (rapides, sans git/coverage) : parsing du patch, arithmétique diff/critical,
  seuils de verdict, démonstration du « masquage » (global élevé, diff faible).
- Acceptation (git réel + coverage.py réel) : scénario en DEUX temps —
    A) branche gouvernance ajoutée SANS test  -> CI verte mais CHANGE_NOT_SUFFICIENTLY_VALIDATED,
       et le dev_agent n'est PAS crédité malgré le vert ;
    B) test de la branche ajouté             -> CHANGE_CONFIRMED, le dev_agent est crédité.
  Le dev_agent apprend ainsi que « vert » ne veut pas dire « suffisamment prouvé ».
"""

from __future__ import annotations

import importlib
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from jarvis_kernel.world.confidence import agent_calibration, change_assurance
from jarvis_kernel.world.coverage_runner import measure_coverage_paths
from jarvis_kernel.world.diff_coverage import (CHANGE_BROKEN, CHANGE_CONFIRMED,
                                               CHANGE_NOT_SUFFICIENTLY_VALIDATED,
                                               DiffCoverageAnalyzer, diff_coverage_report,
                                               git_diff, parse_diff_added_lines, record_change_outcome)
from jarvis_kernel.world.memory_store import UnifiedMemory

# ------------------------------------------------------------------ unitaires (purs)
_PATCH = """\
diff --git a/src/jarvis_kernel/governance/x.py b/src/jarvis_kernel/governance/x.py
--- a/src/jarvis_kernel/governance/x.py
+++ b/src/jarvis_kernel/governance/x.py
@@ -10,0 +11,2 @@ def f():
+    if sensitive:  # GR-2
+        return "require_validation"
@@ -20 +22 @@ def g():
-    return 1
+    return 2
"""


class TestParse(unittest.TestCase):
    def test_added_lines_per_file(self) -> None:
        added = parse_diff_added_lines(_PATCH)
        f = "src/jarvis_kernel/governance/x.py"
        self.assertEqual(added[f], {11, 12, 22})       # 2 lignes du 1er hunk + 1 du second


class TestMath(unittest.TestCase):
    def _cov(self, executable, covered):
        return {"src/jarvis_kernel/governance/x.py": {
            "file": "src/jarvis_kernel/governance/x.py", "lines_total": len(executable),
            "lines_covered": len(covered), "coverage_pct": len(covered) / len(executable),
            "covered_lines": sorted(covered), "executable_lines": sorted(executable)}}

    def test_diff_coverage_ratio_and_masking(self) -> None:
        # global élevé (9/10) mais la ligne critique 12 (require_validation) N'EST PAS couverte
        cov = self._cov(executable=set(range(1, 13)), covered=set(range(1, 12)))  # 11/12 exécutées
        rep = DiffCoverageAnalyzer().analyze("base", "head", _PATCH, cov, root="/nonexistent")
        # lignes modifiées exécutables = {11,12,22} ∩ exécutables{1..12} = {11,12}
        self.assertEqual(rep.findings[0].changed_executable_lines, 2)
        self.assertEqual(rep.findings[0].covered_changed_lines, 1)                # 11 couverte, 12 non
        self.assertAlmostEqual(rep.diff_coverage, 0.5)
        self.assertGreater(rep.module_coverage, rep.diff_coverage)               # 91 % masque 50 %

    def test_change_assurance_is_a_product_never_bypasses(self) -> None:
        # CI verte + diff 100 % mais chemin critique 0 % -> assurance écrasée
        self.assertEqual(change_assurance(True, 1.0, 0.0, True, 0.9), 0.0)
        # tout bon -> proche de la fiabilité de l'analyseur
        self.assertGreater(change_assurance(True, 1.0, 1.0, True, 0.9), 0.8)
        # CI rouge -> 0 quoi qu'il arrive
        self.assertEqual(change_assurance(False, 1.0, 1.0, True, 0.9), 0.0)

    def test_verdicts(self) -> None:
        cov = self._cov(executable={11, 12}, covered={11, 12})                    # tout couvert
        rep = DiffCoverageAnalyzer().analyze("b", "h", _PATCH, cov, root="/nonexistent",
                                             ci_status="success", analyzer_reliability_score=0.9)
        self.assertEqual(rep.verdict, CHANGE_CONFIRMED)
        rep_red = DiffCoverageAnalyzer().analyze("b", "h", _PATCH, cov, root="/nonexistent",
                                                 ci_status="failure")
        self.assertEqual(rep_red.verdict, CHANGE_BROKEN)


# ------------------------------------------------------------------ acceptation (git + coverage RÉELS)
_GOV_BASE = '''\
def classify(action):
    if action == "read":
        return "allow"
    return "review"
'''

_GOV_A = '''\
def classify(action):
    if action == "read":
        return "allow"
    if action == "external":  # GR-2 branche critique
        return "require_validation"
    return "review"
'''

_TEST_BASE = '''\
import unittest

from dcov_canary.governance.gov import classify


class T(unittest.TestCase):
    def test_read(self):
        self.assertEqual(classify("read"), "allow")

    def test_other(self):
        self.assertEqual(classify("write"), "review")
'''

_TEST_B = _TEST_BASE + '''
    def test_external(self):
        self.assertEqual(classify("external"), "require_validation")
'''


def _git(root, *args):
    return subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t",
                           "-c", "commit.gpgsign=false", *args],
                          cwd=str(root), capture_output=True, text=True, timeout=20)


def _write(root, gov, test):
    pkg = root / "src" / "dcov_canary"
    (pkg / "governance").mkdir(parents=True, exist_ok=True)
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "governance" / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "governance" / "gov.py").write_text(gov, encoding="utf-8")
    (root / "tests").mkdir(exist_ok=True)
    (root / "tests" / "test_gov.py").write_text(test, encoding="utf-8")


def _purge():
    for name in list(sys.modules):
        if name.split(".")[0] == "dcov_canary" or name.startswith("test_gov"):
            del sys.modules[name]
    importlib.invalidate_caches()


def _measure(root):
    _purge()
    return measure_coverage_paths(root / "src", root / "tests", source=str(root / "src" / "dcov_canary"),
                                  root=root)


class TestAcceptanceTwoCommits(unittest.TestCase):
    def test_green_is_not_proven_then_confirmed(self) -> None:
        try:
            import coverage  # noqa: F401
        except ImportError:
            self.skipTest("coverage.py absent")

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            if _git(root, "init", "-q", "-b", "main").returncode != 0:
                self.skipTest("git indisponible")

            _write(root, _GOV_BASE, _TEST_BASE)
            _git(root, "add", "-A"); _git(root, "commit", "-q", "-m", "base")
            base = _git(root, "rev-parse", "--short", "HEAD").stdout.strip()

            _write(root, _GOV_A, _TEST_BASE)                       # branche GR-2, AUCUN test
            _git(root, "add", "-A"); _git(root, "commit", "-q", "-m", "A: branche GR-2 sans test")
            sha_a = _git(root, "rev-parse", "--short", "HEAD").stdout.strip()

            _write(root, _GOV_A, _TEST_B)                          # + test de la branche
            _git(root, "add", "-A"); _git(root, "commit", "-q", "-m", "B: test de la branche")
            sha_b = _git(root, "rev-parse", "--short", "HEAD").stdout.strip()

            mem = UnifiedMemory()
            oid = mem.start_episode("ajouter la validation GR-2")
            cal_before = agent_calibration(mem, "dev_agent")

            # ---- COMMIT A : vert mais insuffisamment validé -> pas de crédit ----
            _git(root, "checkout", "-f", "-q", sha_a)
            cov_a = _measure(root)
            self.assertTrue(cov_a, "coverage.py n'a rien mesuré")
            patch_a = git_diff(root, base, sha_a)
            d_a = mem.record_decision(oid, "dev_agent", "ajouter branche GR-2",
                                      entities=["classify", "category:diff_coverage"])
            rep_a = DiffCoverageAnalyzer().analyze(base, sha_a, patch_a, cov_a, root=root,
                                                   decision_id=d_a, ci_status="success",
                                                   behavioral_ok=True)
            self.assertEqual(rep_a.verdict, CHANGE_NOT_SUFFICIENTLY_VALIDATED)
            self.assertLess(rep_a.critical_diff_coverage, 1.0)             # ligne GR-2 non exercée
            self.assertGreater(rep_a.module_coverage, rep_a.critical_diff_coverage)  # masquage
            record_change_outcome(mem, d_a, rep_a)
            cal_after_a = agent_calibration(mem, "dev_agent")
            self.assertEqual(cal_after_a, cal_before)                      # « vert » ≠ crédit

            # ---- COMMIT B : test ajouté -> confirmé -> crédit ----
            _git(root, "checkout", "-f", "-q", sha_b)
            cov_b = _measure(root)
            patch_b = git_diff(root, base, sha_b)
            d_b = mem.record_decision(oid, "dev_agent", "ajouter test de la branche GR-2",
                                      entities=["classify", "category:diff_coverage"])
            rep_b = DiffCoverageAnalyzer().analyze(base, sha_b, patch_b, cov_b, root=root,
                                                   decision_id=d_b, ci_status="success",
                                                   behavioral_ok=True)
            self.assertEqual(rep_b.verdict, CHANGE_CONFIRMED)
            self.assertEqual(rep_b.critical_diff_coverage, 1.0)           # branche GR-2 exercée
            self.assertGreaterEqual(rep_b.diff_coverage, 0.9)
            record_change_outcome(mem, d_b, rep_b)
            cal_after_b = agent_calibration(mem, "dev_agent")
            self.assertGreater(cal_after_b, cal_after_a)                  # seul le changement prouvé crédite


if __name__ == "__main__":
    unittest.main()
