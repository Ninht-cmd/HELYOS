"""Tests de la bibliothèque open-source locale (recherche dans le catalogue TSV)."""

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from jarvis_kernel.integrations.library import OpenSourceLibrary

_TSV = ('"full_name"\t"owner"\t"name"\t"clone_url"\t"html_url"\t"description"\t"language"'
        '\t"stargazers_count"\t"forks_count"\t"archived"\t"fork"\t"source"\t"pushed_at"\n'
        '"Dolibarr/dolibarr"\t"Dolibarr"\t"dolibarr"\t"u"\t"h"\t"ERP and CRM for business,'
        ' invoicing"\t"PHP"\t"6000"\t"3000"\t"False"\t"False"\t"topic:erp"\t"2026"\n'
        '"BerriAI/litellm"\t"BerriAI"\t"litellm"\t"u"\t"h"\t"LLM gateway proxy"\t"Python"'
        '\t"20000"\t"2000"\t"False"\t"False"\t"topic:llm"\t"2026"\n')


class TestLibrary(unittest.TestCase):
    def _lib(self, td: str) -> OpenSourceLibrary:
        root = Path(td)
        (root / "catalogs").mkdir()
        (root / "catalogs" / "github-open-source-catalog-20260719-000000.tsv").write_text(
            _TSV, encoding="utf-8")
        (root / "github" / "Dolibarr" / "dolibarr").mkdir(parents=True)  # cloné en local
        return OpenSourceLibrary(root=root)

    def test_count_and_search_by_need(self) -> None:
        with TemporaryDirectory() as td:
            lib = self._lib(td)
            self.assertEqual(lib.count(), 2)
            hits = lib.search("facturation erp invoicing")
            self.assertTrue(hits)
            self.assertEqual(hits[0]["full_name"], "Dolibarr/dolibarr")
            self.assertTrue(hits[0]["cloned_local"])          # dossier présent -> vrai

    def test_llm_query_finds_litellm(self) -> None:
        with TemporaryDirectory() as td:
            hits = self._lib(td).search("llm gateway")
            self.assertEqual(hits[0]["full_name"], "BerriAI/litellm")
            self.assertFalse(hits[0]["cloned_local"])         # pas de dossier -> non cloné

    def test_no_match_returns_empty(self) -> None:
        with TemporaryDirectory() as td:
            self.assertEqual(self._lib(td).search("quantum blockchain unicorn"), [])

    def test_missing_catalog_is_safe(self) -> None:
        with TemporaryDirectory() as td:
            lib = OpenSourceLibrary(root=Path(td))              # aucun catalogue
            self.assertEqual(lib.count(), 0)
            self.assertEqual(lib.search("erp"), [])


if __name__ == "__main__":
    unittest.main()
