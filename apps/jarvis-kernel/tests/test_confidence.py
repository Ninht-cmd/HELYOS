"""Tests de la confiance composite : prior bayésien, qualité de preuve, fraîcheur,
modes strict/équilibré, montée de fiabilité avec l'expérience, et garde-fou gouvernance."""

from __future__ import annotations

import unittest

from jarvis_kernel.governance.autonomy import AutonomyLevel
from jarvis_kernel.governance.policy import Action, ActionType, Decision
from jarvis_kernel.governance.service import GovernanceService
from jarvis_kernel.world.confidence import (CompositeConfidence, analyzer_reliability,
                                            bayesian_reliability, composite_for,
                                            evidence_quality, source_freshness)
from jarvis_kernel.world.memory_store import UnifiedMemory


def _counter():
    t = [0.0]
    def c():
        t[0] += 1
        return t[0]
    return c


class TestFactors(unittest.TestCase):
    def test_bayesian_prior_avoids_illusion(self) -> None:
        self.assertAlmostEqual(bayesian_reliability(1, 0), 0.6, places=4)      # pas 1.0 !
        self.assertAlmostEqual(bayesian_reliability(11, 3), 13 / 18, places=4)
        self.assertGreater(bayesian_reliability(200, 0), 0.98)                 # le prior s'efface

    def test_evidence_quality_by_nature(self) -> None:
        self.assertEqual(evidence_quality("architecture"), 1.0)
        self.assertGreater(evidence_quality("import_cycle"), evidence_quality("dead_code"))
        self.assertAlmostEqual(evidence_quality("dead_code", 3), 0.72, places=4)  # bonus preuves

    def test_source_freshness_half_life(self) -> None:
        self.assertEqual(source_freshness(0), 1.0)
        self.assertAlmostEqual(source_freshness(30, "source_code"), 0.5, places=3)   # 1 demi-vie
        self.assertAlmostEqual(source_freshness(0.25, "ci"), 0.5, places=3)          # CI H=6h


class TestComposite(unittest.TestCase):
    def test_strict_below_balanced(self) -> None:
        cc = CompositeConfidence(0.92, 0.79, 0.86, 0.98)
        self.assertLess(cc.strict, cc.balanced)                # produit < moyenne géométrique
        self.assertAlmostEqual(cc.strict, 0.92 * 0.79 * 0.86 * 0.98, places=3)
        self.assertTrue(0 < cc.balanced <= 1)

    def test_three_levels(self) -> None:
        L = CompositeConfidence(0.99, 0.70, 0.76, 1.0).levels()
        self.assertEqual(L["observation"], 0.99)               # le fait (CC=26) est quasi certain
        self.assertLess(L["action"], L["observation"])         # la correction est plus discutable
        self.assertTrue(all(0 <= v <= 1 for v in L.values()))


class TestReliabilityLearns(unittest.TestCase):
    def test_reliability_rises_with_confirmed_outcomes(self) -> None:
        m = UnifiedMemory(clock=_counter())
        oid = m.start_episode("obj")
        d = m.record_decision(oid, "dev_agent", "fix", entities=["a", "category:complexity"])
        m.record_outcome(d, observed=1.0, expected=1.0)         # confirmé
        r1, _, _ = analyzer_reliability(m, "complexity")        # (1+2)/(1+4)=0.6
        for i in range(5):
            dd = m.record_decision(oid, "dev_agent", f"f{i}", entities=["x", "category:complexity"])
            m.record_outcome(dd, observed=1.0, expected=1.0)
        r2, c, _ = analyzer_reliability(m, "complexity")        # (6+2)/(6+4)=0.8
        self.assertGreater(r2, r1)
        self.assertEqual(c, 6)
        # la confiance composite d'un nouveau finding monte avec l'expérience
        finding = {"category": "complexity", "evidence": ["CC=26"]}
        self.assertGreater(composite_for(finding, m).balanced,
                           composite_for(finding, None).balanced)


class TestGovernanceGuardrail(unittest.TestCase):
    def test_confidence_never_bypasses_governance(self) -> None:
        # confiance = 1.0 ne doit JAMAIS sauter GR-2
        self.assertEqual(CompositeConfidence(1, 1, 1, 1).balanced, 1.0)
        v = GovernanceService().submit(
            Action(type=ActionType.EXTERNAL_SENSITIVE, actor="dev_agent",
                   description="commit correctif", sensitive=True), AutonomyLevel.A5)
        self.assertIs(v.decision, Decision.REQUIRE_VALIDATION)   # règles d'or au-dessus de la confiance
        self.assertEqual(v.rule, "GR-2")


if __name__ == "__main__":
    unittest.main()
