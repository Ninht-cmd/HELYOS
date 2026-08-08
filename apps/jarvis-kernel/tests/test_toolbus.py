"""Tests du Tool Bus + ProjectConnector : lecture RÉELLE du dépôt, gouvernée."""

from __future__ import annotations

import unittest

from jarvis_kernel.governance.autonomy import AutonomyLevel
from jarvis_kernel.governance.service import GovernanceService
from jarvis_kernel.world.toolbus import GitHubConnector, ProjectConnector, ToolBus, default_bus


class TestProjectConnector(unittest.TestCase):
    def setUp(self) -> None:
        self.c = ProjectConnector()

    def test_reads_real_commits(self) -> None:
        r = self.c.read("commits", n=3)
        self.assertTrue(r.ok)
        self.assertGreaterEqual(len(r.data), 1)                 # le dépôt a des commits réels
        self.assertIn("hash", r.data[0])

    def test_counts_real_modules_and_tests(self) -> None:
        self.assertGreater(self.c.read("modules").data, 50)     # ~80 modules réels
        self.assertGreater(self.c.read("tests").data, 15)

    def test_search_returns_list(self) -> None:
        r = self.c.read("search", pattern=r"def ", limit=5)
        self.assertTrue(r.ok)
        self.assertIsInstance(r.data, list)

    def test_real_static_analysis(self) -> None:
        # analyses réelles (au-delà des TODO/FIXME) : listes exploitables
        self.assertIsInstance(self.c.read("untested").data, list)
        big = self.c.read("large", min_lines=200).data
        self.assertTrue(all(b["lines"] >= 200 for b in big))       # seuil respecté
        dead = self.c.read("deadcode").data
        self.assertTrue(all("name" in d and "file" in d for d in dead))


class TestGitHubConnectorLive(unittest.TestCase):
    """Lecture DISTANTE réelle via l'API publique — résilient si le réseau est indisponible."""

    def test_reads_remote_repo(self) -> None:
        r = GitHubConnector("Ninht-cmd", "HELYOS").read("repo")
        if not r.ok:
            self.skipTest(f"réseau/GitHub indisponible : {r.note}")
        self.assertEqual(r.data["full_name"], "Ninht-cmd/HELYOS")
        self.assertFalse(r.data["private"])                        # dépôt public réel


class TestGovernedBus(unittest.TestCase):
    def setUp(self) -> None:
        self.bus = ToolBus(GovernanceService())
        self.bus.register(ProjectConnector())

    def test_read_gated_by_autonomy(self) -> None:
        # lecture = ANALYZE (A1) : refusée à A0, permise à A1
        self.assertFalse(self.bus.read("project", "commits", granted=AutonomyLevel.A0).ok)
        self.assertTrue(self.bus.read("project", "commits", granted=AutonomyLevel.A1).ok)

    def test_unknown_connector(self) -> None:
        self.assertFalse(self.bus.read("sap", "orders").ok)

    def test_propose_action_requires_validation(self) -> None:
        p = self.bus.propose_action("committer un correctif", granted=AutonomyLevel.A5)
        self.assertEqual(p["decision"], "require_validation")   # jamais autonome (GR-2)
        self.assertEqual(p["rule"], "GR-2")

    def test_default_bus_has_project(self) -> None:
        self.assertIn("project", default_bus(GovernanceService()).connectors())


if __name__ == "__main__":
    unittest.main()
