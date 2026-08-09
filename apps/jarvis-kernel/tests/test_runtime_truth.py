"""Tests runtime-truth : resolver (exécuté ≠ assermenté), couverture comportementale,
et démotion d'un analyseur devenu peu fiable dans le ranking du dev_agent."""

from __future__ import annotations

import unittest

from jarvis_kernel.governance.autonomy import AutonomyLevel
from jarvis_kernel.governance.service import GovernanceService
from jarvis_kernel.world.behavioral_coverage import run_behavioral_coverage
from jarvis_kernel.world.coverage_fusion import CoverageTruthResolver
from jarvis_kernel.world.memory_store import UnifiedMemory
from jarvis_kernel.world.planner import _dev_candidates
from jarvis_kernel.world.toolbus import ProjectConnector, ToolBus

GOV = "apps/jarvis-kernel/src/jarvis_kernel/governance/service.py"
API = "apps/jarvis-kernel/src/jarvis_kernel/api/dashboard.py"


class TestTruthResolver(unittest.TestCase):
    def setUp(self) -> None:
        self.r = CoverageTruthResolver()

    def test_confirmed_flags_critical(self) -> None:
        v = self.r.resolve({"symbol": "submit", "category": "untested", "file": GOV},
                           {GOV: {"coverage_pct": 0.0, "lines_total": 10, "lines_covered": 0}})
        self.assertEqual(v.status, "confirmed")
        self.assertTrue(any("CRITIQUE" in e for e in v.evidence))     # couche sensible à 0 %

    def test_contradicted_distinguishes_executed_from_asserted(self) -> None:
        cov = {API: {"coverage_pct": 0.97, "lines_total": 100, "lines_covered": 97}}
        f = {"symbol": "AgentRegistry", "category": "untested", "file": API}
        v_exec = self.r.resolve(f, cov, symbol_asserted=False)
        self.assertEqual(v_exec.status, "contradicted")
        self.assertTrue(any("exécution ≠ validation" in e for e in v_exec.evidence))  # nuance
        v_assert = self.r.resolve(f, cov, symbol_asserted=True)
        self.assertEqual(v_assert.status, "contradicted")
        self.assertFalse(any("exécution ≠ validation" in e for e in v_assert.evidence))

    def test_unknown_when_unmeasured(self) -> None:
        v = self.r.resolve({"symbol": "x", "category": "untested", "file": "z.py"}, {})
        self.assertEqual(v.status, "unknown")


class TestBehavioralCoverage(unittest.TestCase):
    def test_critical_governance_behaviors_are_exercised(self) -> None:
        r = run_behavioral_coverage()
        self.assertEqual(r["covered"], r["total"])                    # toutes les garanties tenues
        names = {x["behavior"]: x["covered"] for x in r["results"]}
        self.assertTrue(names["external_sensitive_requires_validation"])
        self.assertTrue(names["financial_never_autonomous"])
        self.assertTrue(names["memory_no_repropose"])


class TestRankingDemotesBadAnalyzer(unittest.TestCase):
    def test_low_reliability_category_sinks(self) -> None:
        mem = UnifiedMemory()
        oid = mem.start_episode("x")
        for i in range(8):                                            # untested devient peu fiable
            d = mem.record_decision(oid, "TestCoverageMapper", f"u{i}", entities=["s", "category:untested"])
            mem.set_decision_status(d, "rejected", "faux positif runtime")
        for i in range(8):                                            # complexity reste fiable
            d = mem.record_decision(oid, "dev_agent", f"c{i}", entities=["s", "category:complexity"])
            mem.record_outcome(d, observed=1.0, expected=1.0)
        bus = ToolBus(GovernanceService()); bus.register(ProjectConnector())
        ctx = {"bus": bus, "memory": mem}
        _dev_candidates(ctx)
        findings = ctx["_findings"]
        self.assertNotEqual(findings[0]["category"], "untested")      # ne remonte plus en tête
        i_cplx = next((i for i, f in enumerate(findings) if f["category"] == "complexity"), 999)
        i_unt = next((i for i, f in enumerate(findings) if f["category"] == "untested"), 999)
        self.assertLess(i_cplx, i_unt)                                # complexity (fiable) avant untested


if __name__ == "__main__":
    unittest.main()
