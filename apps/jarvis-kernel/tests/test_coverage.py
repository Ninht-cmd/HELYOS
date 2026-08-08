"""Tests de la fusion AST↔runtime : verdicts confirmé/infirmé, priorité par criticité,
couverture des lignes modifiées, calibration auto, et mesure coverage.py réelle (résiliente)."""

from __future__ import annotations

import unittest
from pathlib import Path

from jarvis_kernel.world.confidence import analyzer_reliability
from jarvis_kernel.world.coverage_fusion import (changed_lines_coverage, fuse_untested,
                                                 priority, record_verifications, verdict)
from jarvis_kernel.world.coverage_runner import measure_coverage
from jarvis_kernel.world.memory_store import UnifiedMemory

ROOT = Path(__file__).resolve().parents[3]
GOV = "apps/jarvis-kernel/src/jarvis_kernel/governance/service.py"
API = "apps/jarvis-kernel/src/jarvis_kernel/api/dashboard.py"


class TestVerdictAndFusion(unittest.TestCase):
    def test_verdict_thresholds(self) -> None:
        self.assertEqual(verdict(0.0), "confirmed")
        self.assertEqual(verdict(0.85), "contradicted")
        self.assertEqual(verdict(0.40), "partial")

    def test_fusion_confirms_and_contradicts(self) -> None:
        ast = [{"category": "untested", "file": API, "symbol": "build_dashboard"},
               {"category": "untested", "file": GOV, "symbol": "submit"}]
        cov = {API: {"lines_total": 50, "lines_covered": 0, "coverage_pct": 0.0},
               GOV: {"lines_total": 40, "lines_covered": 33, "coverage_pct": 0.82}}
        res = {r.symbol: r.runtime_verdict for r in fuse_untested(ast, cov)}
        self.assertEqual(res["build_dashboard"], "confirmed")     # AST avait raison (0 %)
        self.assertEqual(res["submit"], "contradicted")           # faux positif (82 %)


class TestPriorityByCriticality(unittest.TestCase):
    def test_governance_outranks_ui_even_with_more_coverage(self) -> None:
        p_gov = priority(GOV, coverage_pct=0.55, confidence=0.94)   # risque 1.0
        p_ui = priority(API, coverage_pct=0.0, confidence=0.95)     # risque 0.4, 0 % couvert
        self.assertGreater(p_gov, p_ui)      # 55 % en gouvernance > 0 % en UI


class TestChangedLines(unittest.TestCase):
    def test_changed_lines_coverage(self) -> None:
        self.assertAlmostEqual(changed_lines_coverage([1, 2, 3, 5], [2, 3, 4]), 2 / 3, places=4)
        self.assertEqual(changed_lines_coverage([1], []), 1.0)


class TestAutoCalibration(unittest.TestCase):
    def test_runtime_verdicts_update_reliability(self) -> None:
        m = UnifiedMemory()
        oid = m.start_episode("vérifier la couverture")
        ast = [{"category": "untested", "file": API, "symbol": "A"},
               {"category": "untested", "file": GOV, "symbol": "B"}]
        cov = {API: {"lines_total": 10, "lines_covered": 0, "coverage_pct": 0.0},
               GOV: {"lines_total": 10, "lines_covered": 8, "coverage_pct": 0.8}}
        stats = record_verifications(m, oid, fuse_untested(ast, cov))
        self.assertEqual(stats["confirmed"], 1)
        self.assertEqual(stats["contradicted"], 1)
        r, c, rej = analyzer_reliability(m, "untested")            # 1 confirmé, 1 faux positif
        self.assertEqual((c, rej), (1, 1))
        self.assertAlmostEqual(r, 3 / 6, places=4)                # (1+2)/(1+1+4)


class TestRealCoverage(unittest.TestCase):
    """Mesure coverage.py RÉELLE — sur un petit sous-ensemble, résiliente."""

    def test_measures_real_execution(self) -> None:
        cov = measure_coverage(ROOT, pattern="test_confidence.py")
        if not cov:
            self.skipTest("coverage.py indisponible")
        conf = next((v for k, v in cov.items() if k.endswith("world/confidence.py")), None)
        self.assertIsNotNone(conf)
        self.assertGreater(conf["coverage_pct"], 0.5)             # confidence.py réellement exécuté


if __name__ == "__main__":
    unittest.main()
