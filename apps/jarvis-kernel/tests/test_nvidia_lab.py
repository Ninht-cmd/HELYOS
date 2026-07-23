from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from jarvis_kernel.agents.nvidia_lab import NvidiaLabAgent
from jarvis_kernel.agents.open_source_lab import OpenSourceLabAgent
from jarvis_kernel.context import build_default_context
from jarvis_kernel.governance.autonomy import AutonomyLevel
from jarvis_kernel.integrations.nvidia_lab import NvidiaLab
from jarvis_kernel.integrations.open_source_lab import OpenSourceLab


class TestNvidiaLabIntegration(unittest.TestCase):
    def _lab_root(self) -> tempfile.TemporaryDirectory:
        d = tempfile.TemporaryDirectory()
        root = Path(d.name)
        catalogs = root / "catalogs"
        catalogs.mkdir()
        (catalogs / "repos-all-summary-final.json").write_text(
            json.dumps({
                "attempted": 3,
                "by_status": [
                    {"status": "cloned", "count": 1},
                    {"status": "exists", "count": 1},
                    {"status": "fallback_bare", "count": 1},
                ],
                "report": str(catalogs / "github.tsv"),
                "repos_all": str(root / "repos-all"),
            }),
            encoding="utf-8",
        )
        (catalogs / "huggingface-summary-final.json").write_text(
            json.dumps({
                "entries": 4,
                "by_kind_status": [
                    {"kind": "models", "status": "cloned", "count": 2},
                    {"kind": "models", "status": "gated_auth_required", "count": 1},
                    {"kind": "spaces", "status": "exists", "count": 1},
                ],
                "destination": str(root / "huggingface-all-git"),
            }),
            encoding="utf-8",
        )
        artifact = root / "model.gguf"
        artifact.write_text("x", encoding="utf-8")
        (catalogs / "huggingface-lfs-phase3.json").write_text(
            json.dumps([{"name": "test", "size_gb": 0.01, "path": str(artifact)}]),
            encoding="utf-8",
        )
        return d

    def test_reads_catalog_summaries(self) -> None:
        with self._lab_root() as root:
            status = NvidiaLab(root).status()
        self.assertTrue(status["exists"])
        self.assertEqual(status["github"]["attempted"], 3)
        self.assertEqual(status["github"]["local_available"], 3)
        self.assertEqual(status["huggingface"]["entries"], 4)
        self.assertEqual(status["huggingface"]["local_available"], 3)
        self.assertEqual(status["huggingface"]["gated_auth_required"], 1)
        self.assertEqual(status["lfs_artifacts"][0]["exists"], True)

    def test_agent_is_read_only_a0(self) -> None:
        ctx = build_default_context()
        with self._lab_root() as root:
            verdict, status = NvidiaLabAgent(NvidiaLab(root)).snapshot(
                ctx.governance, granted=AutonomyLevel.A0)
        self.assertTrue(verdict.allowed)
        self.assertIsNotNone(status)
        types = [e.action_type for e in ctx.governance.audit.tail(5)]
        self.assertIn("read", types)
        self.assertNotIn("financial", types)

    def test_jarvis_routes_nvidia_status(self) -> None:
        ctx = build_default_context()
        self.assertEqual(ctx.jarvis.classify("etat NVIDIA CUDA et Nemotron"), "nvidia_lab")


class TestOpenSourceLabIntegration(unittest.TestCase):
    def _lab_root(self) -> tempfile.TemporaryDirectory:
        d = tempfile.TemporaryDirectory()
        root = Path(d.name)
        catalogs = root / "catalogs"
        catalogs.mkdir()
        report = catalogs / "clone.tsv"
        report.write_text(
            "full_name\tstatus\tpath\tstars\tlanguage\turl\tdetail\n"
            f"owner/repo\texists\t{root / 'github' / 'owner' / 'repo'}\t10\tPython\thttps://github.com/owner/repo\t\n",
            encoding="utf-8",
        )
        (catalogs / "github-open-source-summary-latest.json").write_text(
            json.dumps({"count": 3, "topics": ["llm"], "catalog_json": "x", "catalog_tsv": "y"}),
            encoding="utf-8",
        )
        (catalogs / "github-open-source-clone-summary-latest.json").write_text(
            json.dumps({
                "attempted": 1,
                "by_status": [{"status": "exists", "count": 1}],
                "destination": str(root / "github"),
                "report": str(report),
            }),
            encoding="utf-8",
        )
        return d

    def test_reads_open_source_summary(self) -> None:
        with self._lab_root() as root:
            status = OpenSourceLab(root).status()
        self.assertEqual(status["catalogued"], 3)
        self.assertEqual(status["local_available"], 1)
        self.assertEqual(status["top_repositories"][0]["full_name"], "owner/repo")

    def test_open_source_agent_is_read_only(self) -> None:
        ctx = build_default_context()
        with self._lab_root() as root:
            verdict, status = OpenSourceLabAgent(OpenSourceLab(root)).snapshot(
                ctx.governance, granted=AutonomyLevel.A0)
        self.assertTrue(verdict.allowed)
        self.assertIsNotNone(status)
        types = [e.action_type for e in ctx.governance.audit.tail(5)]
        self.assertIn("read", types)


if __name__ == "__main__":
    unittest.main()
