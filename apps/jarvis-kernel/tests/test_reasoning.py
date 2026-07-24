"""Tests du cerveau (boucle ReAct). LLM scripté = déterministe, sans réseau.

On prouve le comportement AGENT : le LLM émet une action outil, HELYOS l'exécute
et lui rend le résultat, puis le LLM conclut. C'est ça, l'IA vs la coquille.
"""

from __future__ import annotations

import unittest

from jarvis_kernel.agents.llm import LLMPort
from jarvis_kernel.agents.reasoning import ReasoningAgent
from jarvis_kernel.business.portfolio import seed_known_businesses
from jarvis_kernel.context import build_default_context
from jarvis_kernel.governance.autonomy import AutonomyLevel


class ScriptedLLM(LLMPort):
    """Rend des réponses préprogrammées (une par appel `complete`)."""

    def __init__(self, script: list[str]) -> None:
        self.script = list(script)
        self.prompts: list[str] = []

    def complete(self, prompt: str, **kwargs) -> str:
        self.prompts.append(prompt)
        return self.script.pop(0) if self.script else '{"final": "fin"}'


class TestReasoning(unittest.TestCase):
    def setUp(self) -> None:
        self.ctx = build_default_context()
        seed_known_businesses(self.ctx.portfolio)

    def test_agent_calls_tool_then_concludes(self) -> None:
        # étape 1 : appelle l'outil trésorerie ; étape 2 : conclut avec l'observation
        llm = ScriptedLLM(['{"outil": "tresorerie", "args": ""}',
                           '{"final": "Ta trésorerie est à zéro, priorité : premier encaissement."}'])
        out = ReasoningAgent(self.ctx, llm=llm).run("fais le point sur mon argent")
        self.assertEqual(out["decision"], "allow")
        self.assertEqual(len(out["steps"]), 1)
        self.assertEqual(out["steps"][0]["tool"], "tresorerie")
        self.assertIn("solde", out["steps"][0]["result"])   # vrai résultat d'outil injecté
        self.assertIn("priorité", out["answer"])
        # l'observation a bien été réinjectée dans le 2e prompt (preuve de la boucle)
        self.assertIn("tresorerie(", llm.prompts[1])

    def test_agent_chains_two_tools(self) -> None:
        llm = ScriptedLLM(['{"outil": "portefeuille", "args": ""}',
                           '{"outil": "prospection", "args": ""}',
                           '{"final": "vu."}'])
        out = ReasoningAgent(self.ctx, llm=llm).run("analyse ma situation")
        self.assertEqual([s["tool"] for s in out["steps"]], ["portefeuille", "prospection"])

    def test_unknown_tool_is_skipped_not_crash(self) -> None:
        llm = ScriptedLLM(['{"outil": "licorne", "args": ""}', '{"final": "ok"}'])
        out = ReasoningAgent(self.ctx, llm=llm).run("test")
        self.assertEqual(out["answer"], "ok")
        self.assertEqual(out["steps"], [])                  # l'outil inconnu n'a rien produit

    def test_repeated_tool_call_is_cached_not_reexecuted(self) -> None:
        # anti-répétition : rappeler le même outil ne le ré-exécute pas (efficacité)
        llm = ScriptedLLM(['{"outil": "tresorerie", "args": ""}',
                           '{"outil": "tresorerie", "args": ""}',   # répétition
                           '{"final": "ok"}'])
        out = ReasoningAgent(self.ctx, llm=llm).run("x")
        self.assertEqual(len(out["steps"]), 1)               # une seule exécution réelle
        self.assertIn("déjà obtenu", llm.prompts[2])         # le 3e prompt pousse à conclure

    def test_blocked_below_a1(self) -> None:
        out = ReasoningAgent(self.ctx, llm=ScriptedLLM([])).run("x", granted=AutonomyLevel.A0)
        self.assertIsNone(out["answer"])

    def test_jarvis_routes_reasoning(self) -> None:
        j = self.ctx.jarvis
        self.assertEqual(j.classify("que dois-je faire cette semaine ?"), "raisonnement")
        self.assertEqual(j.classify("analyse ma situation"), "raisonnement")
        # une simple question de caisse reste tresorerie, pas raisonnement
        self.assertEqual(j.classify("bilan de trésorerie"), "tresorerie")


if __name__ == "__main__":
    unittest.main()
