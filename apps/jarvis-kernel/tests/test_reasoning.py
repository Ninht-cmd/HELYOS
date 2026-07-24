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

    def test_action_executes_at_a2_and_changes_state(self) -> None:
        # « vraie action » : à A2, le cerveau enregistre réellement une recette
        svc = "HELYOS Services (automatisation admin)"
        llm = ScriptedLLM([f'{{"outil": "enregistre_recette", "args": "services 90"}}',
                           '{"final": "recette notée."}'])
        out = ReasoningAgent(self.ctx, llm=llm).run("enregistre 90€ pour les services",
                                                    granted=AutonomyLevel.A2)
        self.assertTrue(out["steps"][0]["is_action"])
        self.assertIn("90", out["steps"][0]["result"])
        self.assertEqual(self.ctx.ledger.summary(svc)["recettes_eur"], 90.0)  # état RÉELLEMENT changé

    def test_action_refused_at_a1(self) -> None:
        # à A1, l'action est refusée : le cerveau observe mais n'agit pas
        llm = ScriptedLLM(['{"outil": "enregistre_recette", "args": "services 90"}',
                           '{"final": "je n\'ai pas pu agir."}'])
        out = ReasoningAgent(self.ctx, llm=llm).run("enregistre 90€", granted=AutonomyLevel.A1)
        self.assertIn("refusé", out["steps"][0]["result"])
        g = self.ctx.ledger.global_summary()
        self.assertEqual(g["recettes_eur"], 0.0)                # rien n'a bougé

    def test_brain_has_no_money_out_or_send_tool(self) -> None:
        # garde-fou : aucun outil du cerveau ne paie/envoie/supprime (GR-7/GR-2 hors du cerveau)
        agent = ReasoningAgent(self.ctx)
        for k in agent._tools:
            self.assertNotIn(k, ("payer", "virement", "envoyer", "supprimer", "publier"))

    def test_refused_action_never_narrates_success(self) -> None:
        # honnêteté : à A1, même si le LLM prétend "enregistrée avec succès",
        # la réponse dit clairement que rien n'a été modifié.
        class LyingLLM(LLMPort):
            def __init__(self): self.n = 0
            def complete(self, prompt, **k):
                self.n += 1
                if self.n == 1:
                    return '{"outil": "enregistre_recette", "args": "services 120"}'
                return '{"final": "La recette a été enregistrée avec succès."}'
        self.ctx.jarvis.llm = LyingLLM()
        r = self.ctx.jarvis.handle("objectif: enregistre 120 pour services",
                                   granted=AutonomyLevel.A1)
        self.assertIn("NON fait", r.text)
        self.assertNotIn("avec succès", r.text)              # le mensonge est écarté
        self.assertIn("rien modifié", r.text.lower())

    def test_jarvis_routes_reasoning(self) -> None:
        j = self.ctx.jarvis
        self.assertEqual(j.classify("que dois-je faire cette semaine ?"), "raisonnement")
        self.assertEqual(j.classify("analyse ma situation"), "raisonnement")
        # une simple question de caisse reste tresorerie, pas raisonnement
        self.assertEqual(j.classify("bilan de trésorerie"), "tresorerie")


if __name__ == "__main__":
    unittest.main()
