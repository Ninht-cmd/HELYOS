"""Read-only status reader for OPEN-SOURCE-LAB."""

from __future__ import annotations

import csv
import json
import os
import shutil
import time
from pathlib import Path
from typing import Any


def default_open_source_root() -> Path:
    env = os.environ.get("OPEN_SOURCE_LAB_ROOT")
    candidates = []
    if env:
        candidates.append(Path(env))
    home = Path.home()
    candidates.extend([
        home / "WORKSPACE" / "OPEN-SOURCE-LAB",
        Path(r"C:\Users\emezr\WORKSPACE\OPEN-SOURCE-LAB"),
        Path(r"C:\Users\emeri\WORKSPACE\OPEN-SOURCE-LAB"),
    ])
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def _json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return default


def _tsv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            return list(csv.DictReader(f, delimiter="\t"))
    except Exception:
        return []


def _status_count(items: list[dict[str, Any]]) -> dict[str, int]:
    out: dict[str, int] = {}
    for item in items or []:
        status = str(item.get("status", "unknown"))
        out[status] = out.get(status, 0) + int(item.get("count", 0) or 0)
    return out


class OpenSourceLab:
    def __init__(self, root: str | os.PathLike[str] | None = None) -> None:
        self.root = Path(root) if root is not None else default_open_source_root()
        self.catalogs = self.root / "catalogs"

    def disk_status(self) -> dict[str, float]:
        target = self.root if self.root.exists() else Path.cwd()
        usage = shutil.disk_usage(str(target))
        gb = 1024 ** 3
        return {
            "total_gb": round(usage.total / gb, 2),
            "used_gb": round(usage.used / gb, 2),
            "free_gb": round(usage.free / gb, 2),
        }

    def local_inventory(self) -> dict[str, int]:
        github_dir = self.root / "github"
        bare_dir = self.root / "github-bare-fallback"
        working_tree = 0
        if github_dir.exists():
            for owner_dir in github_dir.iterdir():
                if not owner_dir.is_dir():
                    continue
                working_tree += sum(1 for repo_dir in owner_dir.iterdir() if repo_dir.is_dir())
        bare_fallback = 0
        if bare_dir.exists():
            bare_fallback = sum(1 for repo_dir in bare_dir.iterdir() if repo_dir.is_dir() and repo_dir.name.endswith(".git"))
        return {
            "working_tree": working_tree,
            "bare_fallback": bare_fallback,
            "total": working_tree + bare_fallback,
        }

    def status(self) -> dict[str, Any]:
        catalog = _json(self.catalogs / "github-open-source-summary-latest.json", {})
        clone = _json(self.catalogs / "github-open-source-clone-summary-latest.json", {})
        by_status = _status_count(clone.get("by_status", []))
        local = by_status.get("cloned", 0) + by_status.get("exists", 0) + by_status.get("fallback_bare", 0)
        attempted = int(clone.get("attempted", 0) or 0)
        catalogued = int(catalog.get("count", 0) or 0)
        report = Path(clone["report"]) if clone.get("report") else Path()
        top = _tsv(report)[:20] if report else []
        inventory = self.local_inventory()
        parts = {
            "root": 20 if self.root.exists() else 0,
            "catalog": 30 if catalogued else 0,
            "clones": round(min(1.0, local / attempted) * 40) if attempted else 0,
            "disk": 10 if self.disk_status()["free_gb"] >= 50 else 0,
        }
        return {
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "root": str(self.root),
            "exists": self.root.exists(),
            "catalogued": catalogued,
            "attempted": attempted,
            "local_available": local,
            "local_total": inventory["total"],
            "local_inventory": inventory,
            "by_status": by_status,
            "topics": catalog.get("topics", []),
            "catalog_json": catalog.get("catalog_json", ""),
            "catalog_tsv": catalog.get("catalog_tsv", ""),
            "report": clone.get("report", ""),
            "destination": clone.get("destination", str(self.root / "github")),
            "disk": self.disk_status(),
            "top_repositories": top,
            "readiness": {"score": min(100, sum(parts.values())), "parts": parts},
        }
