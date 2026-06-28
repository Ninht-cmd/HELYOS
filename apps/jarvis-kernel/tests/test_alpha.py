"""Tests des fondations Alpha : mémoire persistante (1), tracing (2), Scribe (3)."""

import tempfile
import unittest
from pathlib import Path

from jarvis_kernel.agents.scribe import ScribeAgent, render_adr
from jarvis_kernel.context import build_default_context
from jarvis_kernel.governance.autonomy import AutonomyLevel
from jarvis_kernel.governance.policy import ActionType, Decision
from jarvis_kernel.memory import build_memory
from jarvis_kernel.memory.sqlite_store import SqliteMemoryStore
from jarvis_kernel.memory.vector import NaiveVectorMemory
from jarvis_kernel.observability import is_enabled, setup_tracing, span


class TestSqliteMemoryPersists(unittest.TestCase):
    def test_persistence_across_reopen(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "mem.sqlite"
            store = SqliteMemoryStore(path)
            store.remember("vision", {"cap": "long terme"}, namespace="codex")
            store.close()
            # Réouverture : la donnée doit avoir survécu (vraie persistance).
            store2 = SqliteMemoryStore(path)
            self.assertEqual(store2.recall("vision", namespace="codex"), {"cap": "long terme"})
            self.assertEqual(len(store2.all("codex")), 1)
            store2.close()

    def test_search_and_forget(self):
        with tempfile.TemporaryDirectory() as d:
            store = SqliteMemoryStore(Path(d) / "m.sqlite")
            store.remember("a", "le Codex est la source de vérité")
            store.remember("b", "local first")
            self.assertEqual(len(store.search("codex")), 1)
            self.assertTrue(store.forget("a"))
            self.assertFalse(store.forget("a"))
            store.close()

    def test_build_memory_factory(self):
        from jarvis_kernel.memory.store import InMemoryMemoryStore

        self.assertIsInstance(build_memory("memory"), InMemoryMemoryStore)
        with tempfile.TemporaryDirectory() as d:
            store = build_memory("sqlite", path=str(Path(d) / "f.sqlite"))
            self.assertIsInstance(store, SqliteMemoryStore)
            store.close()  # libère le fichier (Windows verrouille sinon)
        with self.assertRaises(ValueError):
            build_memory("postgres")  # DSN manquant
        with self.assertRaises(ValueError):
            build_memory("bogus")


class TestVectorMemory(unittest.TestCase):
    def test_semantic_ish_search(self):
        vm = NaiveVectorMemory()
        vm.add("1", "gouvernance autonomie graduée A0 A5 règles d'or")
        vm.add("2", "boucle économique recherche produits revenus patrimoine")
        hits = vm.search("règles de gouvernance et autonomie", limit=2)
        self.assertTrue(hits)
        self.assertEqual(hits[0].id, "1")  # le doc gouvernance ressort en tête


class TestTracingDegradesGracefully(unittest.TestCase):
    def test_noop_when_disabled(self):
        self.assertFalse(setup_tracing(enabled=False))
        self.assertFalse(is_enabled())
        # le context manager span ne doit jamais lever, même sans tracer
        with span("test.span", foo="bar"):
            pass


class TestScribeAgent(unittest.TestCase):
    def setUp(self):
        self.ctx = build_default_context()
        self.scribe = ScribeAgent()

    def test_render_adr_format(self):
        text = render_adr(42, "Titre", "Contexte ici", "Décision ici", adn="2, 4")
        self.assertIn("# ADR-0042 — Titre", text)
        self.assertIn("Décision ici", text)
        self.assertIn("ScribeAgent", text)

    def test_propose_is_write_local_a2(self):
        action = self.scribe.propose({"number": 7, "title": "Choisir X"})
        self.assertEqual(action.type, ActionType.WRITE_LOCAL)
        self.assertEqual(self.scribe.required_level, AutonomyLevel.A2)

    def test_draft_blocked_without_a2(self):
        with tempfile.TemporaryDirectory() as d:
            verdict, path = self.scribe.draft_adr(
                self.ctx.governance, number=10, title="Test",
                context="c", decision="d", granted=AutonomyLevel.A1, adr_dir=d,
            )
            self.assertEqual(verdict.decision, Decision.REQUIRE_VALIDATION)
            self.assertIsNone(path)  # rien écrit sans le niveau requis

    def test_draft_writes_file_when_authorized(self):
        with tempfile.TemporaryDirectory() as d:
            verdict, path = self.scribe.draft_adr(
                self.ctx.governance, number=11, title="Adopter SQLite",
                context="Besoin de persistance locale.", decision="On utilise SQLite.",
                consequences="Persistance sans service externe.", adn="2, 4",
                granted=AutonomyLevel.A2, adr_dir=d, memory=self.ctx.memory,
            )
            self.assertEqual(verdict.decision, Decision.ALLOW)
            self.assertIsNotNone(path)
            self.assertTrue(Path(path).exists())
            content = Path(path).read_text(encoding="utf-8")
            self.assertIn("ADR-0011 — Adopter SQLite", content)
            # La décision est mémorisée (namespace decisions).
            self.assertIsNotNone(self.ctx.memory.recall("ADR-0011", namespace="decisions"))

    def test_index_codex_into_memory(self):
        with tempfile.TemporaryDirectory() as d:
            codex = Path(d)
            (codex / "sec").mkdir()
            (codex / "00_Vision.md").write_text("# Vision\nlocal first", encoding="utf-8")
            (codex / "sec" / "01_ADN.md").write_text("# ADN\nmodularité", encoding="utf-8")
            n = self.scribe.index_codex(self.ctx.governance, self.ctx.memory, codex)
            self.assertEqual(n, 2)
            self.assertEqual(self.ctx.memory.recall("00_Vision.md", namespace="codex"),
                             "# Vision\nlocal first")

    def test_scribe_registered_in_context(self):
        self.assertIn("scribe", self.ctx.registry)
        self.assertEqual(self.ctx.registry.get("scribe").required_level, AutonomyLevel.A2)


if __name__ == "__main__":
    unittest.main()
