"""Tests du service de gouvernance (audit + bus) et de la mémoire."""

import unittest

from jarvis_kernel.context import build_default_context
from jarvis_kernel.governance.autonomy import AutonomyLevel
from jarvis_kernel.governance.policy import Action, ActionType
from jarvis_kernel.memory.store import InMemoryMemoryStore


class TestGovernanceService(unittest.TestCase):
    def setUp(self):
        self.ctx = build_default_context()

    def test_submit_audits_and_emits(self):
        events = []
        self.ctx.bus.subscribe("action.*", events.append)
        v = self.ctx.governance.submit(
            Action(type=ActionType.READ, actor="tester"), AutonomyLevel.A0
        )
        self.assertTrue(v.allowed)
        # une entrée d'audit a été créée
        self.assertEqual(len(self.ctx.governance.audit), 1)
        entry = self.ctx.governance.audit.all()[0]
        self.assertEqual(entry.decision, "allow")
        self.assertEqual(entry.actor, "tester")
        # un événement action.allowed a circulé
        self.assertEqual([e.name for e in events], ["action.allowed"])

    def test_denied_action_is_audited(self):
        self.ctx.governance.submit(
            Action(type=ActionType.DELETE, has_backup=False, actor="cleaner"),
            AutonomyLevel.A5,
        )
        denied = self.ctx.governance.audit.by_decision("deny")
        self.assertEqual(len(denied), 1)
        self.assertEqual(denied[0].rule, "GR-1")

    def test_default_context_has_observer_agent(self):
        self.assertIn("observer", self.ctx.registry)
        observer = self.ctx.registry.get("observer")
        self.assertEqual(observer.required_level, AutonomyLevel.A0)
        # l'agent observateur ne propose que de la lecture
        action = observer.propose({"target": "salon"})
        self.assertEqual(action.type, ActionType.READ)


class TestMemory(unittest.TestCase):
    def setUp(self):
        self.mem = InMemoryMemoryStore()

    def test_remember_and_recall(self):
        self.mem.remember("cap", "vision long terme", namespace="codex")
        self.assertEqual(self.mem.recall("cap", namespace="codex"), "vision long terme")
        self.assertIsNone(self.mem.recall("absent"))

    def test_forget(self):
        self.mem.remember("k", "v")
        self.assertTrue(self.mem.forget("k"))
        self.assertFalse(self.mem.forget("k"))

    def test_search(self):
        self.mem.remember("a", "le Codex est la source de vérité")
        self.mem.remember("b", "local first")
        hits = self.mem.search("codex")
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0].key, "a")

    def test_namespaces_are_isolated(self):
        self.mem.remember("k", "x", namespace="ns1")
        self.assertIsNone(self.mem.recall("k", namespace="ns2"))


if __name__ == "__main__":
    unittest.main()
