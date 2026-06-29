"""Tests de l'orchestration d'agents composés sous gouvernance (RFC-0004)."""

import unittest

from jarvis_kernel.agents.llm import StubLLM
from jarvis_kernel.agents.orchestrator import Orchestrator, Step
from jarvis_kernel.agents.research import ResearchAgent
from jarvis_kernel.agents.scribe import ScribeAgent
from jarvis_kernel.context import build_default_context
from jarvis_kernel.governance.autonomy import AutonomyLevel
from jarvis_kernel.governance.policy import ActionType, Decision


class TestStubLLM(unittest.TestCase):
    def test_deterministic(self):
        llm = StubLLM()
        out = llm.complete("Bonjour   le\nmonde")
        self.assertEqual(out, llm.complete("Bonjour le monde"))  # normalise + déterministe
        self.assertIn("synthèse", out)


class TestResearchAgent(unittest.TestCase):
    def setUp(self):
        self.ctx = build_default_context()
        self.agent = ResearchAgent()

    def test_propose_is_analyze_a1(self):
        action = self.agent.propose({"topic": "gouvernance"})
        self.assertEqual(action.type, ActionType.ANALYZE)
        self.assertEqual(self.agent.required_level, AutonomyLevel.A1)

    def test_blocked_below_a1(self):
        verdict, finding = self.agent.analyze(self.ctx.governance, "x", granted=AutonomyLevel.A0)
        self.assertEqual(verdict.decision, Decision.REQUIRE_VALIDATION)
        self.assertIsNone(finding)

    def test_produces_and_stores_finding(self):
        verdict, finding = self.agent.analyze(
            self.ctx.governance, "fusion HELYOS Jarvis",
            granted=AutonomyLevel.A1, memory=self.ctx.memory,
        )
        self.assertEqual(verdict.decision, Decision.ALLOW)
        self.assertIsNotNone(finding)
        self.assertEqual(self.ctx.memory.recall("fusion HELYOS Jarvis", namespace="research"),
                         finding)


class TestOrchestrator(unittest.TestCase):
    def setUp(self):
        self.ctx = build_default_context()
        self.orch = Orchestrator(self.ctx.governance)
        self.steps = [
            Step(ResearchAgent(), {"topic": "mémoire vectorielle"}),
            Step(ScribeAgent(), {"number": 99, "title": "issue de l'analyse"}),
        ]

    def test_full_chain_allowed_at_a2(self):
        results = self.orch.run(self.steps, AutonomyLevel.A2)
        self.assertEqual(len(results), 2)
        self.assertTrue(all(r.allowed for r in results))
        self.assertEqual([r.agent for r in results], ["research", "scribe"])

    def test_halts_when_a_step_is_blocked(self):
        # En A1 : research (A1) passe, scribe (A2) bloque -> arrêt.
        events = []
        self.ctx.bus.subscribe("orchestrator.*", events.append)
        results = self.orch.run(self.steps, AutonomyLevel.A1)
        self.assertEqual(len(results), 2)
        self.assertTrue(results[0].allowed)            # research ok
        self.assertFalse(results[1].allowed)           # scribe bloqué
        self.assertEqual(results[1].verdict.decision, Decision.REQUIRE_VALIDATION)
        self.assertIn("orchestrator.halted", [e.name for e in events])

    def test_composition_is_audited(self):
        self.orch.run(self.steps, AutonomyLevel.A2)
        # 2 étapes => au moins 2 entrées d'audit (gouvernance traversée à chaque étape).
        self.assertGreaterEqual(len(self.ctx.governance.audit), 2)


if __name__ == "__main__":
    unittest.main()
