"""Read-only NVIDIA Lab integration.

The lab lives outside the kernel. HELYOS only reads reports and runtime probes
so the cockpit can reason from real local state instead of promises.
"""

from __future__ import annotations

import csv
import json
import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any


def _round_gb(bytes_count: int) -> float:
    return round(bytes_count / (1024 ** 3), 2)


def _first_existing(candidates: list[Path]) -> Path:
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def default_lab_root() -> Path:
    env = os.environ.get("NVIDIA_LAB_ROOT")
    candidates: list[Path] = []
    if env:
        candidates.append(Path(env))
    home = Path.home()
    candidates.extend(
        [
            home / "WORKSPACE" / "NVIDIA-LAB",
            Path(r"C:\Users\emezr\WORKSPACE\NVIDIA-LAB"),
            Path(r"C:\Users\emeri\WORKSPACE\NVIDIA-LAB"),
        ]
    )
    return _first_existing(candidates)


def _run(cmd: list[str], timeout: float = 2.5) -> dict[str, Any]:
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding="utf-8",
            errors="replace",
        )
    except FileNotFoundError:
        return {"ok": False, "error": "not_found", "cmd": cmd[0]}
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "timeout", "cmd": cmd[0]}
    return {
        "ok": proc.returncode == 0,
        "returncode": proc.returncode,
        "stdout": proc.stdout.strip(),
        "stderr": proc.stderr.strip(),
        "cmd": cmd[0],
    }


class NvidiaLab:
    """Read NVIDIA-LAB reports and cheap local runtime probes."""

    def __init__(self, root: str | os.PathLike[str] | None = None) -> None:
        self.root = Path(root) if root is not None else default_lab_root()
        self.catalogs = self.root / "catalogs"

    def _json(self, name: str, default: Any) -> Any:
        path = self.catalogs / name
        try:
            return json.loads(path.read_text(encoding="utf-8-sig"))
        except Exception:
            return default

    def _latest(self, pattern: str) -> Path | None:
        if not self.catalogs.exists():
            return None
        files = sorted(self.catalogs.glob(pattern), key=lambda p: p.stat().st_mtime)
        return files[-1] if files else None

    def _count_tsv_statuses(self, path: Path | None, status_field: str = "status") -> dict[str, int]:
        if path is None or not path.exists():
            return {}
        counts: dict[str, int] = {}
        try:
            with path.open("r", encoding="utf-8-sig", newline="") as f:
                for row in csv.DictReader(f, delimiter="\t"):
                    status = str(row.get(status_field, "")).strip() or "unknown"
                    counts[status] = counts.get(status, 0) + 1
        except Exception:
            return {}
        return counts

    @staticmethod
    def _status_count(items: list[dict[str, Any]], key: str = "status") -> dict[str, int]:
        out: dict[str, int] = {}
        for item in items:
            status = str(item.get(key, "unknown"))
            try:
                count = int(item.get("count", 0))
            except (TypeError, ValueError):
                count = 0
            out[status] = out.get(status, 0) + count
        return out

    def github_summary(self) -> dict[str, Any]:
        data = self._json("repos-all-summary-final.json", {})
        by_status = self._status_count(data.get("by_status", []))
        report = Path(data["report"]) if data.get("report") else self._latest("clone-all-report-*.tsv")
        if not by_status:
            by_status = self._count_tsv_statuses(report)
        attempted = int(data.get("attempted") or sum(by_status.values()) or 0)
        local = by_status.get("cloned", 0) + by_status.get("exists", 0) + by_status.get("fallback_bare", 0)
        return {
            "attempted": attempted,
            "local_available": local,
            "by_status": by_status,
            "report": str(report) if report else "",
            "repos_all": str(data.get("repos_all") or (self.root / "repos-all")),
            "bare_fallback": str(data.get("bare_fallback") or (self.root / "repos-linux-only" / "all")),
            "fallback_list": str(data.get("fallback_list") or ""),
        }

    def huggingface_summary(self) -> dict[str, Any]:
        data = self._json("huggingface-summary-final.json", {})
        by_kind_status = data.get("by_kind_status", [])
        counts: dict[str, dict[str, int]] = {}
        for item in by_kind_status:
            kind = str(item.get("kind", "unknown"))
            status = str(item.get("status", "unknown"))
            counts.setdefault(kind, {})[status] = counts.setdefault(kind, {}).get(status, 0) + int(item.get("count", 0))
        entries = int(data.get("entries") or sum(sum(v.values()) for v in counts.values()) or 0)
        cloned = sum(v.get("cloned", 0) + v.get("exists", 0) for v in counts.values())
        gated = sum(v.get("gated_auth_required", 0) for v in counts.values())
        return {
            "entries": entries,
            "local_available": cloned,
            "gated_auth_required": gated,
            "by_kind_status": counts,
            "destination": str(data.get("destination") or (self.root / "huggingface-all-git")),
            "size_gb": data.get("size_gb", 0),
            "report": str(data.get("report") or self._latest("huggingface-clone-report-*.tsv") or ""),
        }

    def lfs_artifacts(self) -> list[dict[str, Any]]:
        items = self._json("huggingface-lfs-phase3.json", [])
        if not isinstance(items, list):
            return []
        return [
            {
                "name": str(item.get("name", "")),
                "size_gb": float(item.get("size_gb", 0) or 0),
                "path": str(item.get("path", "")),
                "exists": Path(str(item.get("path", ""))).exists(),
            }
            for item in items
        ]

    def gpu_status(self) -> dict[str, Any]:
        res = _run(
            [
                "nvidia-smi",
                "--query-gpu=name,driver_version,memory.total,memory.used,utilization.gpu,temperature.gpu",
                "--format=csv,noheader,nounits",
            ],
            timeout=3,
        )
        if not res["ok"]:
            return {"available": False, "detail": res.get("error") or res.get("stderr", "")}
        line = res["stdout"].splitlines()[0] if res["stdout"] else ""
        parts = [p.strip() for p in line.split(",")]
        if len(parts) < 6:
            return {"available": True, "raw": line}
        return {
            "available": True,
            "name": parts[0],
            "driver": parts[1],
            "memory_total_mib": int(float(parts[2])),
            "memory_used_mib": int(float(parts[3])),
            "utilization_pct": int(float(parts[4])),
            "temperature_c": int(float(parts[5])),
        }

    def docker_status(self) -> dict[str, Any]:
        res = _run(["docker", "images", "nvidia/cuda", "--format", "{{.Repository}}:{{.Tag}}"], timeout=4)
        if not res["ok"]:
            return {"available": False, "detail": res.get("error") or res.get("stderr", "")}
        images = [line for line in res["stdout"].splitlines() if line.strip()]
        wanted = ("nvidia/cuda:13.3.0-base-ubuntu24.04", "nvidia/cuda:13.3.0-devel-ubuntu24.04")
        return {
            "available": True,
            "images": images,
            "cuda_13_3_ready": all(tag in images for tag in wanted),
        }

    def _ollama_exe(self) -> str:
        env = os.environ.get("OLLAMA_EXE")
        candidates = [
            env,
            shutil.which("ollama"),
            str(Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Ollama" / "ollama.exe"),
            r"C:\Users\emezr\AppData\Local\Programs\Ollama\ollama.exe",
        ]
        for candidate in candidates:
            if candidate and Path(candidate).exists():
                return candidate
        return "ollama"

    def ollama_status(self) -> dict[str, Any]:
        exe = self._ollama_exe()
        listed = _run([exe, "list"], timeout=4)
        running = _run([exe, "ps"], timeout=4)
        model_name = "nvidia-nemotron3-nano-4b:latest"
        models_text = listed.get("stdout", "") if listed["ok"] else ""
        running_text = running.get("stdout", "") if running["ok"] else ""
        return {
            "available": bool(listed["ok"]),
            "exe": exe,
            "nemotron_model": model_name,
            "model_installed": model_name in models_text,
            "model_running": model_name in running_text,
            "running": running_text.splitlines()[1:] if running["ok"] and running_text else [],
            "detail": "" if listed["ok"] else listed.get("error") or listed.get("stderr", ""),
        }

    def runtime_status(self) -> dict[str, Any]:
        return {
            "gpu": self.gpu_status(),
            "docker": self.docker_status(),
            "ollama": self.ollama_status(),
        }

    def disk_status(self) -> dict[str, Any]:
        target = self.root if self.root.exists() else self.root.anchor or Path.cwd()
        try:
            usage = shutil.disk_usage(str(target))
        except Exception:
            usage = shutil.disk_usage(str(Path.cwd()))
        return {
            "total_gb": _round_gb(usage.total),
            "used_gb": _round_gb(usage.used),
            "free_gb": _round_gb(usage.free),
        }

    @staticmethod
    def _ratio_score(done: int, total: int, points: int) -> int:
        if total <= 0:
            return 0
        return round(min(1.0, done / total) * points)

    def status(self) -> dict[str, Any]:
        github = self.github_summary()
        hf = self.huggingface_summary()
        lfs = self.lfs_artifacts()
        runtime = self.runtime_status()
        parts = {
            "root": 10 if self.root.exists() else 0,
            "github": self._ratio_score(github["local_available"], github["attempted"], 25),
            "huggingface": self._ratio_score(hf["local_available"], hf["entries"], 20),
            "lfs": self._ratio_score(sum(1 for item in lfs if item["exists"]), len(lfs), 10),
            "gpu": 15 if runtime["gpu"].get("available") else 0,
            "docker": 10 if runtime["docker"].get("cuda_13_3_ready") else 0,
            "ollama": 10 if runtime["ollama"].get("model_running") else 5 if runtime["ollama"].get("model_installed") else 0,
        }
        score = min(100, sum(parts.values()))
        return {
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "root": str(self.root),
            "exists": self.root.exists(),
            "github": github,
            "huggingface": hf,
            "lfs_artifacts": lfs,
            "runtime": runtime,
            "disk": self.disk_status(),
            "readiness": {"score": score, "parts": parts},
        }
