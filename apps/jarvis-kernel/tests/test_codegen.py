"""Tests génération de livrables : code qui compile, plans, routage déterministe.

On prouve que le cerveau PRODUIT (fichier écrit, code vérifié), pas qu'il narre.
LLM factice = déterministe, sans réseau.
"""

from __future__ import annotations

import os
import re
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from jarvis_kernel.agents.llm import LLMPort
from jarvis_kernel.agents.reasoning import ReasoningAgent
from jarvis_kernel.context import build_default_context
from jarvis_kernel.governance.autonomy import AutonomyLevel
from jarvis_kernel.integrations.codegen import (
    _detect_language, _extract_code, business_plan, engineering_plan, generate_code)
from jarvis_kernel.jarvis import Jarvis


class FakeLLM(LLMPort):
    """Rend un bloc de code fencé, ou un plan Markdown si le prompt le demande."""

    def __init__(self, code: str = "print('bonjour HELYOS')", lang: str = "python") -> None:
        self.code, self.lang = code, lang

    def complete(self, prompt: str, **kwargs) -> str:
        if "Markdown" in prompt:
            return "## Objectif\nGagner de l'argent proprement.\n\n## Risques\nAucun garanti.\n"
        return f"```{self.lang}\n{self.code}\n```"


class TestCodegenCore(unittest.TestCase):
    def test_detect_language(self) -> None:
        self.assertEqual(_detect_language("écris du javascript"), "javascript")
        self.assertEqual(_detect_language("un script go"), "go")
        self.assertEqual(_detect_language("un truc sans langage"), "python")  # défaut

    def test_extract_code_strips_fences_and_think(self) -> None:
        raw = "<think>je réfléchis</think>\nVoici :\n```python\nx = 1\n```"
        self.assertEqual(_extract_code(raw), "x = 1")

    def test_generate_valid_python_compiles(self) -> None:
        with TemporaryDirectory() as td:
            r = generate_code("affiche bonjour", FakeLLM(), out_dir=td)
            self.assertTrue(r["ok"])
            self.assertEqual(r["language"], "python")
            self.assertTrue(r["verified"])                  # py_compile a réussi
            self.assertTrue(Path(r["path"]).exists())
            self.assertIn("bonjour HELYOS", Path(r["path"]).read_text(encoding="utf-8"))

    def test_generate_broken_python_flags_failure(self) -> None:
        with TemporaryDirectory() as td:
            r = generate_code("code cassé", FakeLLM(code="def (:\n  pass"), out_dir=td)
            self.assertTrue(r["ok"])                         # fichier écrit…
            self.assertFalse(r["verified"])                  # …mais ne compile pas (honnête)
            self.assertTrue(r["error"])

    def test_plans_write_structured_files(self) -> None:
        with TemporaryDirectory() as td:
            e = engineering_plan("un banc d'essai moteur", FakeLLM(), out_dir=td)
            b = business_plan("vendre l'espace dirigeant", FakeLLM(), out_dir=td)
            for r in (e, b):
                self.assertTrue(r["ok"])
                self.assertEqual(r["sections"], 2)           # 2 sections dans le faux plan
                self.assertGreater(r["chars"], 40)
                self.assertTrue(Path(r["path"]).read_text(encoding="utf-8").startswith("# "))


class TestBrainGenerationTools(unittest.TestCase):
    def setUp(self) -> None:
        self.ctx = build_default_context()

    def test_tools_registered_as_actions(self) -> None:
        a = ReasoningAgent(self.ctx)
        for t in ("genere_code", "plan_ingenierie", "plan_business"):
            self.assertIn(t, a._tools)
            self.assertIn(t, a._actions)                     # écrit un fichier -> A2

    def test_refused_at_a1_produces_no_lie(self) -> None:
        a = ReasoningAgent(self.ctx, llm=FakeLLM())
        a._granted = AutonomyLevel.A1
        out = a._a_genere_code("affiche bonjour")
        self.assertTrue(out.startswith("["))                 # refus honnête, pas un faux succès

    def test_succeeds_at_a2_and_writes_file(self) -> None:
        a = ReasoningAgent(self.ctx, llm=FakeLLM())
        a._granted = AutonomyLevel.A2
        out = a._a_genere_code("affiche bonjour")
        self.assertIn("généré", out)
        self.assertIn("compile", out)
        m = re.search(r": (.+?) \(", out)
        if m and os.path.exists(m.group(1)):
            os.unlink(m.group(1))                            # nettoyage


class TestGenerationRouting(unittest.TestCase):
    def setUp(self) -> None:
        self.j = Jarvis(build_default_context())

    def test_routes_to_generation(self) -> None:
        for msg in ("génère un script python qui affiche bonjour",
                    "écris-moi une fonction javascript de tri",
                    "fais-moi un plan business pour vendre l'espace dirigeant",
                    "un plan d'ingénierie pour un banc de test moteur"):
            self.assertEqual(self.j.classify(msg), "generation", msg)

    def test_guards_do_not_over_capture(self) -> None:
        # « génère une pièce » reste au cerveau (STL), pas génération de code
        self.assertEqual(self.j.classify("génère une pièce engrenage dents=12"), "raisonnement")
        # « relance mes factures » reste au flux factures
        self.assertEqual(self.j.classify("relance mes factures impayées"), "relance_factures")

    def test_handler_a2_writes_a1_refuses(self) -> None:
        j = Jarvis(self.ctx if hasattr(self, "ctx") else build_default_context(), llm=FakeLLM())
        r2 = j._generation("génère un script python qui affiche bonjour", AutonomyLevel.A2)
        self.assertEqual(r2.intent, "generation")
        self.assertTrue(r2.text.startswith("✅ Fait"))
        m = re.search(r": (.+?) \(", r2.text)
        if m and os.path.exists(m.group(1)):
            os.unlink(m.group(1))
        r1 = j._generation("génère un script python qui affiche bonjour", AutonomyLevel.A1)
        self.assertTrue(r1.text.startswith("⛔ NON fait"))


if __name__ == "__main__":
    unittest.main()
