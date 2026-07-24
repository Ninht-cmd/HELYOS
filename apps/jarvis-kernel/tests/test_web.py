"""Tests de l'accès web du cerveau — dont le garde-fou SSRF (sécurité)."""

from __future__ import annotations

import unittest

from jarvis_kernel.integrations.web import _is_public, web_fetch


class TestWebGuards(unittest.TestCase):
    def test_ssrf_blocks_localhost_and_private(self) -> None:
        # le cerveau ne doit JAMAIS pouvoir sonder les services internes
        self.assertFalse(_is_public("localhost"))
        self.assertFalse(_is_public("127.0.0.1"))
        self.assertFalse(_is_public("192.168.1.1"))
        self.assertFalse(_is_public("10.0.0.5"))
        self.assertFalse(_is_public("169.254.169.254"))     # métadonnées cloud

    def test_fetch_rejects_non_http(self) -> None:
        self.assertIn("http(s) requis", web_fetch("file:///etc/passwd"))
        self.assertIn("http(s) requis", web_fetch("ftp://x"))

    def test_fetch_rejects_private_url(self) -> None:
        self.assertIn("refusé", web_fetch("http://127.0.0.1:8080/health"))
        self.assertIn("refusé", web_fetch("http://localhost/admin"))


class TestBrainHasWebTools(unittest.TestCase):
    def test_brain_exposes_web_tools(self) -> None:
        from jarvis_kernel.agents.reasoning import ReasoningAgent
        from jarvis_kernel.context import build_default_context
        agent = ReasoningAgent(build_default_context())
        self.assertIn("cherche_web", agent._tools)
        self.assertIn("lis_page", agent._tools)
        # ce sont des lectures (A1), pas des actions A2
        self.assertNotIn("cherche_web", agent._actions)
        self.assertNotIn("lis_page", agent._actions)


if __name__ == "__main__":
    unittest.main()
