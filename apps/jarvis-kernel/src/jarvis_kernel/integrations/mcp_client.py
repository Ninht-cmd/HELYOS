"""Client MCP — le « se branche à TOUT » de HELYOS, proprement.

« Un Jarvis qui se branche à tout » = un client MCP (Model Context Protocol,
le standard). Au lieu de coder un connecteur par service, HELYOS parle UN
protocole et atteint n'importe quel serveur MCP de l'écosystème (fichiers,
Gmail, Slack, Postgres, GitHub… des centaines existent).

Doctrine (cohérente avec tout le reste) :
- DÉCOUVRIR les outils d'un serveur = lecture (A1), libre.
- APPELER un outil externe = action sur le monde → EXTERNAL_SENSITIVE, donc
  validation humaine (GR-2). « Fait tout », oui — mais jamais l'irréversible
  sans toi. C'est ce qui sépare un assistant utile d'une bombe.
- Rien n'est branché tant que ce n'est pas déclaré dans mcp_servers.json.
  On ne prétend jamais parler à un service qu'on ne peut pas joindre.

Transport stdio JSON-RPC (le même que notre propre serveur mcp_server.py).
Testable sans sous-processus via un runner injecté.
"""

from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

PROTOCOL_VERSION = "2024-11-05"


@dataclass
class MCPServerSpec:
    name: str
    command: list[str]
    cwd: str = ""
    env: dict = field(default_factory=dict)


def load_specs(path: str | os.PathLike | None = None) -> list[MCPServerSpec]:
    """Lit mcp_servers.json (repo). Toujours au moins la boucle 'helyos-self' pour
    prouver que le client marche, sans dépendre d'un service externe."""
    # .../HELYOS/apps/jarvis-kernel/src/jarvis_kernel/integrations/mcp_client.py
    # parents: [0]integrations [1]jarvis_kernel [2]src [3]jarvis-kernel [4]apps [5]HELYOS
    repo = Path(__file__).resolve().parents[5]
    cfg = Path(path) if path else repo / "mcp_servers.json"
    specs: list[MCPServerSpec] = []
    if cfg.exists():
        try:
            data = json.loads(cfg.read_text(encoding="utf-8-sig"))
            for s in data.get("servers", []):
                specs.append(MCPServerSpec(name=s["name"], command=s["command"],
                                           cwd=s.get("cwd", ""), env=s.get("env", {})))
        except Exception:
            pass
    if not specs:                       # défaut : se parler à soi-même (dogfooding)
        src = str(repo / "apps" / "jarvis-kernel" / "src")
        specs.append(MCPServerSpec(
            name="helyos-self", command=["python", "-m", "jarvis_kernel.mcp_server"],
            cwd=str(repo), env={"PYTHONPATH": src}))
    return specs


class MCPClient:
    """Parle à UN serveur MCP par session stdio (lance, initialise, requête, ferme)."""

    def __init__(self, spec: MCPServerSpec, runner=None, timeout: float = 20.0) -> None:
        self.spec = spec
        self.timeout = timeout
        self._runner = runner or self._subprocess_runner   # injectable pour les tests

    def _subprocess_runner(self, requests: list[dict]) -> list[dict]:
        """Lance le serveur, envoie initialize + requêtes, renvoie les réponses."""
        env = {**os.environ, **self.spec.env}
        lines = [json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize",
                             "params": {"protocolVersion": PROTOCOL_VERSION,
                                        "capabilities": {}, "clientInfo": {"name": "helyos"}}}),
                 json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"})]
        lines += [json.dumps({"jsonrpc": "2.0", **r}) for r in requests]
        proc = subprocess.run(
            self.spec.command, input="\n".join(lines) + "\n",
            capture_output=True, text=True, timeout=self.timeout,
            cwd=self.spec.cwd or None, env=env)
        out = []
        for ln in proc.stdout.splitlines():
            ln = ln.strip()
            if not ln or not ln.startswith("{"):
                continue
            try:
                out.append(json.loads(ln))
            except json.JSONDecodeError:
                continue
        return out

    def list_tools(self) -> list[dict]:
        resp = self._runner([{"id": 2, "method": "tools/list"}])
        for r in resp:
            if r.get("id") == 2 and "result" in r:
                return r["result"].get("tools", [])
        return []

    def call_tool(self, name: str, arguments: dict | None = None) -> dict:
        resp = self._runner([{"id": 3, "method": "tools/call",
                              "params": {"name": name, "arguments": arguments or {}}}])
        for r in resp:
            if r.get("id") == 3:
                if "error" in r:
                    return {"error": r["error"].get("message", "erreur")}
                return r.get("result", {})
        return {"error": "aucune réponse"}
