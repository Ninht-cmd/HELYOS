"""HELYOS — Tool Bus + connecteurs réels (brique #4 : connexion au monde réel).

Architecture commune : les agents ne parlent pas directement aux outils ; ils passent
par un BUS gouverné. Toute LECTURE est une action ANALYZE (A1) ; toute écriture/action
externe passe en REQUIRE_VALIDATION (A0–A5). On ne se branche pas au monde sans garde-fou.

Premier connecteur réel : `ProjectConnector` lit le VRAI dépôt HELYOS (git local) —
commits, fichiers modifiés, marqueurs TODO/FIXME, inventaire des modules/tests. Aucune
authentification, aucune dépendance réseau : une source réelle fiable pour démarrer.
Gmail/Calendar/GitHub-API/SQL suivront le même patron (un `read(op, **params)` par connecteur).
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from ..governance.autonomy import AutonomyLevel
from ..governance.policy import Action, ActionType, Decision


@dataclass
class ReadResult:
    connector: str
    op: str
    ok: bool
    data: object = None
    source: str = ""
    note: str = ""


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[5]


class ProjectConnector:
    """Lit l'état RÉEL du dépôt (git + système de fichiers). Lecture seule."""
    name = "project"

    def __init__(self, root: str | Path | None = None) -> None:
        self.root = Path(root) if root else _repo_root()

    def _git(self, *args: str) -> str:
        try:
            r = subprocess.run(["git", *args], cwd=str(self.root), capture_output=True,
                               text=True, timeout=8)
            return r.stdout.strip() if r.returncode == 0 else ""
        except Exception:
            return ""

    def read(self, op: str, **p) -> ReadResult:
        src = f"git://{self.root.name}"
        if op == "commits":
            out = self._git("log", "--oneline", "-n", str(p.get("n", 5)))
            rows = [{"hash": l.split(" ", 1)[0], "sujet": l.split(" ", 1)[1] if " " in l else ""}
                    for l in out.splitlines() if l]
            return ReadResult(self.name, op, True, rows, src)
        if op == "status":
            out = self._git("status", "--porcelain")
            rows = [{"etat": l[:2].strip(), "fichier": l[3:]} for l in out.splitlines() if l]
            return ReadResult(self.name, op, True, rows, src)
        if op == "search":
            pattern = re.compile(p.get("pattern", r"TODO|FIXME|XXX"))
            hits, base = [], self.root / "apps" / "jarvis-kernel" / "src"
            for f in base.rglob("*.py"):
                try:
                    for i, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
                        if pattern.search(line):
                            hits.append({"fichier": str(f.relative_to(self.root)), "ligne": i,
                                         "texte": line.strip()[:100]})
                            if len(hits) >= p.get("limit", 50):
                                return ReadResult(self.name, op, True, hits, str(base), "limite atteinte")
                except Exception:
                    continue
            return ReadResult(self.name, op, True, hits, str(base))
        if op == "modules":
            base = self.root / "apps" / "jarvis-kernel" / "src"
            return ReadResult(self.name, op, True, sum(1 for _ in base.rglob("*.py")), str(base))
        if op == "tests":
            base = self.root / "apps" / "jarvis-kernel" / "tests"
            return ReadResult(self.name, op, True, sum(1 for _ in base.glob("test_*.py")), str(base))
        return ReadResult(self.name, op, False, None, src, f"opération inconnue : {op}")


class ToolBus:
    """Bus gouverné : les agents lisent le monde par ici ; les actions sont soumises à A0–A5."""

    def __init__(self, governance=None) -> None:
        self._connectors: dict[str, object] = {}
        self.gov = governance

    def register(self, connector) -> None:
        self._connectors[connector.name] = connector

    def connectors(self) -> list[str]:
        return list(self._connectors)

    def read(self, connector: str, op: str, *, granted: AutonomyLevel = AutonomyLevel.A1, **params) -> ReadResult:
        c = self._connectors.get(connector)
        if c is None:
            return ReadResult(connector, op, False, None, "", "connecteur inconnu")
        if self.gov is not None:                     # lecture = ANALYZE (A1)
            v = self.gov.submit(Action(type=ActionType.ANALYZE, actor=f"bus:{connector}",
                                       description=f"lire {connector}.{op}"), granted)
            if v.decision is not Decision.ALLOW:
                return ReadResult(connector, op, False, None, "", f"lecture refusée : {v.reason}")
        return c.read(op, **params)

    def propose_action(self, description: str, *, granted: AutonomyLevel = AutonomyLevel.A2) -> dict:
        """Une action à effet externe/sensible n'est jamais autonome : elle revient en
        REQUIRE_VALIDATION (GR-2), en attente de validation humaine."""
        if self.gov is None:
            return {"description": description, "decision": "no_governance", "rule": None}
        v = self.gov.submit(Action(type=ActionType.EXTERNAL_SENSITIVE, actor="tool_bus",
                                   description=description, sensitive=True), granted)
        return {"description": description, "decision": v.decision.value, "rule": v.rule, "reason": v.reason}


def default_bus(governance=None) -> ToolBus:
    bus = ToolBus(governance)
    bus.register(ProjectConnector())
    return bus
