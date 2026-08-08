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
        # --- analyse logicielle réelle (au-delà des TODO/FIXME) ---
        if op in ("untested", "large", "deadcode"):
            return self._analyze(op, **p)
        return ReadResult(self.name, op, False, None, src, f"opération inconnue : {op}")

    # ---- analyses statiques (heuristiques honnêtes : des SIGNAUX, pas des certitudes) ----
    def _src_files(self):
        base = self.root / "apps" / "jarvis-kernel" / "src"
        return [f for f in base.rglob("*.py") if "__pycache__" not in str(f)]

    def _analyze(self, op: str, **p) -> ReadResult:
        src = "analyse statique (arbre local)"
        files = self._src_files()
        if op == "large":                              # modules volumineux (signal de complexité)
            thr = p.get("min_lines", 250)
            big = sorted(({"file": str(f.relative_to(self.root)),
                           "lines": len(f.read_text(encoding="utf-8").splitlines())}
                          for f in files), key=lambda x: -x["lines"])
            return ReadResult(self.name, op, True, [b for b in big if b["lines"] >= thr][:10], src)
        if op == "untested":                           # modules dont le nom n'apparaît dans AUCUN test
            tests_dir = self.root / "apps" / "jarvis-kernel" / "tests"
            test_text = " ".join(t.read_text(encoding="utf-8") for t in tests_dir.glob("test_*.py"))
            mods = {f.stem for f in files if f.stem not in ("__init__", "__main__")}
            untested = sorted(m for m in mods if m not in test_text)
            return ReadResult(self.name, op, True, untested, src)
        if op == "deadcode":                           # défs de haut niveau jamais référencées ailleurs
            all_text = "\n".join(f.read_text(encoding="utf-8") for f in files)
            cands = []
            for f in files:
                for line in f.read_text(encoding="utf-8").splitlines():
                    m = re.match(r"^(?:def|class)\s+([A-Za-z]\w+)", line)
                    if not m:
                        continue
                    name = m.group(1)
                    if name.startswith("_") or name in ("main", "create_app", "serve"):
                        continue
                    if len(re.findall(rf"\b{re.escape(name)}\b", all_text)) <= 1:   # 1 = sa propre déf
                        cands.append({"name": name, "file": str(f.relative_to(self.root))})
            return ReadResult(self.name, op, True, cands[:15], src)
        return ReadResult(self.name, op, False, None, src, f"analyse inconnue : {op}")


class GitHubConnector:
    """Lit le dépôt DISTANT via l'API publique GitHub (repos publics : sans authentification).
    Lecture réelle sur le réseau — repo, commits, issues, pull requests, langages."""
    name = "github"

    def __init__(self, owner: str = "Ninht-cmd", repo: str = "HELYOS") -> None:
        self.owner, self.repo = owner, repo

    def _get(self, path: str):
        import json
        import urllib.request
        req = urllib.request.Request(
            f"https://api.github.com/{path}",
            headers={"User-Agent": "HELYOS", "Accept": "application/vnd.github+json"})
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.load(r)

    def read(self, op: str, **p) -> ReadResult:
        base = f"repos/{self.owner}/{self.repo}"
        src = f"https://github.com/{self.owner}/{self.repo}"
        try:
            if op == "repo":
                d = self._get(base)
                data = {"full_name": d["full_name"], "language": d.get("language"),
                        "stars": d.get("stargazers_count"), "private": d.get("private"),
                        "open_issues": d.get("open_issues_count"), "pushed_at": d.get("pushed_at")}
                return ReadResult(self.name, op, True, data, src)
            if op == "commits":
                d = self._get(f"{base}/commits?per_page={p.get('n', 5)}")
                rows = [{"sha": c["sha"][:7], "message": c["commit"]["message"].splitlines()[0][:80],
                         "author": c["commit"]["author"]["name"]} for c in d]
                return ReadResult(self.name, op, True, rows, src)
            if op == "issues":
                d = self._get(f"{base}/issues?state=open&per_page={p.get('n', 10)}")
                rows = [{"number": i["number"], "title": i["title"][:80]}
                        for i in d if "pull_request" not in i]
                return ReadResult(self.name, op, True, rows, src)
            if op == "pulls":
                d = self._get(f"{base}/pulls?state=open&per_page={p.get('n', 10)}")
                return ReadResult(self.name, op, True,
                                  [{"number": pr["number"], "title": pr["title"][:80]} for pr in d], src)
            if op == "languages":
                return ReadResult(self.name, op, True, self._get(f"{base}/languages"), src)
            return ReadResult(self.name, op, False, None, src, f"opération inconnue : {op}")
        except Exception as e:                          # réseau / rate-limit : échec honnête, pas de crash
            return ReadResult(self.name, op, False, None, src, f"GitHub indisponible : {type(e).__name__}")


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
    bus.register(GitHubConnector())
    return bus
