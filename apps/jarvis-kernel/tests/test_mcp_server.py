"""Tests du serveur MCP (accès Claude -> kernel). Sans E/S : handle_request direct.

Vérité à protéger : le serveur MCP n'ajoute AUCUN pouvoir — un Claude qui demande
une action dangereuse se fait gouverner comme tout le monde.
"""

from __future__ import annotations

import json
import unittest

from jarvis_kernel.context import build_default_context
from jarvis_kernel.business.portfolio import seed_known_businesses
from jarvis_kernel.mcp_server import TOOLS, handle_request


def _payload(resp: dict) -> object:
    return json.loads(resp["result"]["content"][0]["text"])


class TestMCPServer(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.ctx = build_default_context()
        seed_known_businesses(cls.ctx.portfolio)

    def _call(self, name: str, args: dict | None = None) -> dict:
        return handle_request(self.ctx, {
            "jsonrpc": "2.0", "id": 1, "method": "tools/call",
            "params": {"name": name, "arguments": args or {}},
        })

    def test_initialize_and_tools_list(self) -> None:
        r = handle_request(self.ctx, {"jsonrpc": "2.0", "id": 1, "method": "initialize"})
        self.assertEqual(r["result"]["serverInfo"]["name"], "helyos")
        r = handle_request(self.ctx, {"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        self.assertEqual([t["name"] for t in r["result"]["tools"]],
                         [t["name"] for t in TOOLS])

    def test_notifications_get_no_response(self) -> None:
        self.assertIsNone(handle_request(self.ctx, {"jsonrpc": "2.0",
                                                    "method": "notifications/initialized"}))

    def test_status_and_portfolio(self) -> None:
        st = _payload(self._call("helyos_status"))
        self.assertGreaterEqual(len(st["agents"]), 6)
        folio = _payload(self._call("helyos_portfolio"))
        self.assertGreaterEqual(len(folio), 4)

    def test_claude_cannot_bypass_governance(self) -> None:
        # un Claude branché en MCP demande une suppression : refus GR-1, comme tout le monde
        out = _payload(self._call("helyos_ask", {
            "message": "supprime toute la base clients", "granted_level": "A5"}))
        self.assertEqual(out["decision"], "deny")
        self.assertEqual(out["rule"], "GR-1")

    def test_unknown_tool_is_an_error_not_a_crash(self) -> None:
        r = self._call("helyos_nuke")
        self.assertIn("error", r)

    def test_unknown_method(self) -> None:
        r = handle_request(self.ctx, {"jsonrpc": "2.0", "id": 9, "method": "resources/list"})
        self.assertEqual(r["error"]["code"], -32601)


if __name__ == "__main__":
    unittest.main()
