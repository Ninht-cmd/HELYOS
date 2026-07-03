"""Tests du BusinessScaffolder — génération gouvernée + publication qui exige validation."""

import unittest

from jarvis_kernel.agents.business_scaffolder import DISCLAIMER, BusinessScaffolder
from jarvis_kernel.context import build_default_context
from jarvis_kernel.governance.autonomy import AutonomyLevel
from jarvis_kernel.governance.policy import Decision


class TestBusinessScaffolder(unittest.TestCase):
    def setUp(self):
        self.ctx = build_default_context()
        self.agent = BusinessScaffolder()

    def test_registered_in_context(self):
        self.assertIn("business_scaffolder", self.ctx.registry)

    def test_scaffold_blocked_below_a1(self):
        v, plan = self.agent.scaffold(self.ctx.governance, "Boutique X", "animaux",
                                      granted=AutonomyLevel.A0)
        self.assertEqual(v.decision, Decision.REQUIRE_VALIDATION)
        self.assertIsNone(plan)

    def test_scaffold_produces_plan(self):
        v, plan = self.agent.scaffold(self.ctx.governance, "Atelier Compagnon",
                                      "portraits d'animaux personnalisés",
                                      granted=AutonomyLevel.A1, memory=self.ctx.memory)
        self.assertEqual(v.decision, Decision.ALLOW)
        self.assertEqual(len(plan.products), 5)
        self.assertGreaterEqual(len(plan.required_pages), 6)
        self.assertTrue(plan.human_checklist)
        self.assertEqual(plan.disclaimer, DISCLAIMER)  # honnêteté : pas de garantie de revenu
        # mémorisé
        self.assertIsNotNone(self.ctx.memory.recall("Atelier Compagnon", namespace="business"))

    def test_publish_requires_human_validation_even_at_a5(self):
        _, plan = self.agent.scaffold(self.ctx.governance, "X", "y", granted=AutonomyLevel.A1)
        v = self.agent.propose_publish(self.ctx.governance, plan, "Shopify",
                                       granted=AutonomyLevel.A5, validated=False)
        self.assertEqual(v.decision, Decision.REQUIRE_VALIDATION)
        self.assertEqual(v.rule, "GR-2")  # action externe sensible

    def test_publish_allowed_when_validated(self):
        _, plan = self.agent.scaffold(self.ctx.governance, "X", "y", granted=AutonomyLevel.A1)
        v = self.agent.propose_publish(self.ctx.governance, plan, "Shopify",
                                       granted=AutonomyLevel.A2, validated=True)
        self.assertEqual(v.decision, Decision.ALLOW)


if __name__ == "__main__":
    unittest.main()
