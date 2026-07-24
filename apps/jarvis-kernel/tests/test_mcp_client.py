"""Tests du client MCP (le « se branche à tout »). Runner injecté = pas de sous-processus."""

from __future__ import annotations

import unittest

from jarvis_kernel.integrations.mcp_client import MCPClient, MCPServerSpec, load_specs


def _fake_runner(requests):
    """Simule un serveur MCP : répond à tools/list et tools/call."""
    out = []
    for r in requests:
        if r["method"] == "tools/list":
            out.append({"jsonrpc": "2.0", "id": r["id"],
                        "result": {"tools": [{"name": "helyos_status", "description": "état"}]}})
        elif r["method"] == "tools/call":
            name = r["params"]["name"]
            if name == "inconnu":
                out.append({"jsonrpc": "2.0", "id": r["id"],
                            "error": {"code": -32000, "message": "outil inconnu"}})
            else:
                out.append({"jsonrpc": "2.0", "id": r["id"],
                            "result": {"content": [{"type": "text", "text": "ok"}]}})
    return out


class TestMCPClient(unittest.TestCase):
    def _client(self):
        return MCPClient(MCPServerSpec("fake", ["x"]), runner=_fake_runner)

    def test_list_tools(self) -> None:
        tools = self._client().list_tools()
        self.assertEqual(tools[0]["name"], "helyos_status")

    def test_call_tool_ok(self) -> None:
        res = self._client().call_tool("helyos_status")
        self.assertIn("content", res)

    def test_call_tool_error_is_surfaced(self) -> None:
        res = self._client().call_tool("inconnu")
        self.assertIn("error", res)

    def test_default_spec_is_helyos_self(self) -> None:
        # sans config, on se branche au moins sur soi-même (dogfooding)
        specs = load_specs()
        self.assertTrue(any(s.name == "helyos-self" for s in specs))


if __name__ == "__main__":
    unittest.main()
