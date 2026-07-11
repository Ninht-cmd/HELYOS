"""Serveur MCP d'HELYOS — donne à Claude (Desktop, Code, agents) l'accès au kernel VIVANT.

Lancer :
    python -m jarvis_kernel.mcp_server

Brancher dans Claude Code :
    claude mcp add helyos -- python -m jarvis_kernel.mcp_server
(ou dans claude_desktop_config.json : {"mcpServers": {"helyos": {"command": "python",
 "args": ["-m", "jarvis_kernel.mcp_server"], "env": {"PYTHONPATH": "<repo>/apps/jarvis-kernel/src"}}}})

Protocole : MCP sur stdio (JSON-RPC 2.0, un message par ligne). Implémentation
stdlib pure — c'est aussi la première brique du « bus d'agents MCP » de la spec
noyau V1 (RFC-0008 : chantier V2+, entamé ici côté serveur).

Gouvernance : ce serveur n'ajoute AUCUN pouvoir. Claude passe par Jarvis et les
mêmes règles d'or que tout le monde : lire = A0/A1, agir dehors = validation
humaine (GR-2/GR-7). Un Claude qui demande « supprime tout » se fait refuser
comme n'importe qui.
"""

from __future__ import annotations

import json
import sys
from typing import Any

from .context import KernelContext, build_default_context
from .governance.autonomy import AutonomyLevel

PROTOCOL_VERSION = "2024-11-05"

TOOLS: list[dict[str, Any]] = [
    {"name": "helyos_status",
     "description": "État du kernel HELYOS : version, agents, gouvernance, portefeuille.",
     "inputSchema": {"type": "object", "properties": {}}},
    {"name": "helyos_ask",
     "description": ("Parler à Jarvis (point d'entrée unifié d'HELYOS) en langage naturel. "
                     "Les actions sensibles sont gouvernées : le refus fait partie de la réponse."),
     "inputSchema": {"type": "object", "required": ["message"], "properties": {
         "message": {"type": "string"},
         "granted_level": {"type": "string", "description": "A0..A5 (défaut A1)"}}}},
    {"name": "helyos_portfolio",
     "description": "Portefeuille de business réel (statuts, métriques, tâches).",
     "inputSchema": {"type": "object", "properties": {}}},
    {"name": "helyos_audit",
     "description": "Journal d'audit de gouvernance (décisions récentes).",
     "inputSchema": {"type": "object", "properties": {
         "limit": {"type": "integer", "minimum": 1, "maximum": 100}}}},
    {"name": "helyos_connectors",
     "description": "Carte des connecteurs : connecté / à connecter / interdit (et pourquoi).",
     "inputSchema": {"type": "object", "properties": {}}},
    {"name": "helyos_briefing",
     "description": ("Briefing proactif du Pouls : validations en attente, tâches humaines "
                     "bloquantes, mouvements de marché, connecteurs. S'il n'y a rien, il le dit."),
     "inputSchema": {"type": "object", "properties": {}}},
]


def _text(payload: Any) -> dict[str, Any]:
    return {"content": [{"type": "text",
                         "text": json.dumps(payload, ensure_ascii=False, indent=1)}]}


def call_tool(ctx: KernelContext, name: str, args: dict[str, Any]) -> dict[str, Any]:
    if name == "helyos_status":
        return _text({
            "app": ctx.settings.app_name, "version": ctx.settings.version,
            "agents": [a.describe() for a in ctx.registry.list()],
            "decisions_gouvernees": len(ctx.governance.audit),
            "businesses": len(ctx.portfolio.list()),
        })
    if name == "helyos_ask":
        granted = AutonomyLevel.from_name(args.get("granted_level") or "A1")
        r = ctx.jarvis.handle(str(args.get("message", "")), granted=granted)
        return _text({"intent": r.intent, "text": r.text, "governed": r.governed,
                      "decision": r.decision, "rule": r.rule})
    if name == "helyos_portfolio":
        return _text([{**b.to_dict()} for b in ctx.portfolio.list()])
    if name == "helyos_audit":
        limit = max(1, min(int(args.get("limit", 10)), 100))
        return _text([e.to_dict() for e in ctx.governance.audit.tail(limit)])
    if name == "helyos_connectors":
        return _text([c.status().to_dict() for c in (ctx.connectors or [])])
    if name == "helyos_briefing":
        if ctx.pulse is None:
            raise ValueError("Pouls indisponible")
        return _text({"briefing": ctx.pulse.briefing()})
    raise ValueError(f"outil inconnu : {name}")


def handle_request(ctx: KernelContext, req: dict[str, Any]) -> dict[str, Any] | None:
    """Traite UN message JSON-RPC. Retourne la réponse, ou None (notification)."""
    method, req_id = req.get("method", ""), req.get("id")
    if req_id is None:                      # notification (ex. notifications/initialized)
        return None
    try:
        if method == "initialize":
            result: Any = {"protocolVersion": PROTOCOL_VERSION,
                           "capabilities": {"tools": {}},
                           "serverInfo": {"name": "helyos", "version": ctx.settings.version}}
        elif method == "tools/list":
            result = {"tools": TOOLS}
        elif method == "tools/call":
            params = req.get("params") or {}
            result = call_tool(ctx, params.get("name", ""), params.get("arguments") or {})
        elif method == "ping":
            result = {}
        else:
            return {"jsonrpc": "2.0", "id": req_id,
                    "error": {"code": -32601, "message": f"méthode inconnue : {method}"}}
        return {"jsonrpc": "2.0", "id": req_id, "result": result}
    except Exception as exc:               # une erreur d'outil ne tue pas le serveur
        return {"jsonrpc": "2.0", "id": req_id,
                "error": {"code": -32000, "message": str(exc)[:300]}}


def serve(stdin=None, stdout=None) -> None:  # pragma: no cover - boucle E/S
    """Boucle stdio : un message JSON-RPC par ligne. Testé via handle_request."""
    import logging

    stdin = stdin or sys.stdin
    stdout = stdout or sys.stdout

    # stdout appartient AU PROTOCOLE : les logs du kernel partent sur stderr,
    # sinon chaque ligne de log corrompt la session MCP du client.
    kernel_logger = logging.getLogger("helyos")
    kernel_logger.handlers.clear()
    kernel_logger.addHandler(logging.StreamHandler(stream=sys.stderr))

    ctx = build_default_context()
    for line in stdin:
        line = line.strip()
        # tolère un BOM/préfixe parasite (ex. pipe PowerShell) devant le JSON
        brace = line.find("{")
        if brace > 0:
            line = line[brace:]
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError:
            continue
        resp = handle_request(ctx, req)
        if resp is not None:
            stdout.write(json.dumps(resp, ensure_ascii=False) + "\n")
            stdout.flush()


if __name__ == "__main__":  # pragma: no cover
    serve()
