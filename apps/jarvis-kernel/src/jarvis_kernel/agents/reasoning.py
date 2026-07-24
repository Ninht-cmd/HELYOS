"""Le cerveau — la boucle de raisonnement qui transforme HELYOS de menu en IA.

Un menu : tu demandes X → un handler répond X. Une IA : tu donnes un OBJECTIF →
elle décide elle-même quels outils lire, les enchaîne, observe, et raisonne
jusqu'à une réponse. C'est la différence entre une coquille et une intelligence.

Motif ReAct (marche avec le simple /api/generate de qwen3:14b) :
  objectif → le LLM émet une action JSON {"outil","args"} → HELYOS exécute
  l'outil (gouverné, lecture A1) → le résultat est rendu au LLM → il recommence
  → jusqu'à {"final": "..."} ou la limite d'étapes.

Sécurité : les outils du cerveau sont TOUS en LECTURE (A1). Le cerveau observe
et propose ; il ne dépense, ne signe, ne supprime jamais tout seul (GR-2/GR-7
restent la frontière). Une IA qui agit sur le monde sans validation n'est pas
un Jarvis, c'est un incident.
"""

from __future__ import annotations

import json
import re
from typing import Any, Callable

from ..governance.autonomy import AutonomyLevel
from ..governance.policy import Action, ActionType, Decision
from ..governance.service import GovernanceService
from .base import Agent
from .llm import LLMPort, StubLLM


class ReasoningAgent(Agent):
    name = "reasoning"
    description = ("Le cerveau : reçoit un objectif, choisit et enchaîne ses outils "
                   "de lecture, raisonne, synthétise. Ne fait qu'observer (A1).")
    required_level = AutonomyLevel.A1

    def __init__(self, ctx, llm: LLMPort | None = None) -> None:
        self.ctx = ctx
        self.llm = llm or StubLLM()
        self._tools: dict[str, Callable[[str], str]] = {
            "portefeuille": self._t_portfolio,
            "tresorerie": self._t_treasury,
            "prospection": self._t_prospection,
            "commandes": self._t_orders,
            "marche": self._t_market,
            "bibliotheque": self._t_library,
        }

    # ---- outils (lecture seule ; chaque appel renvoie un texte compact pour le LLM) ----
    def _t_portfolio(self, _arg: str) -> str:
        biz = self.ctx.portfolio.list()
        return "; ".join(f"{b.name}: {b.status} ({b.open_tasks} tâches)" for b in biz) or "aucun business"

    def _t_treasury(self, _arg: str) -> str:
        g = self.ctx.ledger.global_summary() if self.ctx.ledger else {}
        return (f"recettes {g.get('recettes_eur', 0):.0f}€, dépenses {g.get('depenses_eur', 0):.0f}€, "
                f"solde {g.get('solde_eur', 0):.0f}€")

    def _t_prospection(self, _arg: str) -> str:
        from ..business.prospection import ProspectionPipeline
        s = ProspectionPipeline(self.ctx.memory).stats()
        return f"{s['total']} prospects, {s['contactes']} contactés, {s['clients']} clients, {s['a_relancer']} à relancer"

    def _t_orders(self, _arg: str) -> str:
        from ..business.orders import OrderBook
        s = OrderBook(self.ctx.memory).summary()
        return (f"{s['ventes']} ventes ({s['a_livrer']} à livrer, {s['a_encaisser_eur']:.0f}€ à encaisser), "
                f"{s['achats']} achats")

    def _t_market(self, arg: str) -> str:
        from .market_analyst import DEFAULT_SYMBOLS, SYMBOLS, MarketAnalystAgent
        m = (arg or "").lower()
        wanted = tuple(dict.fromkeys(p for w, p in SYMBOLS.items() if w in m)) or DEFAULT_SYMBOLS
        try:
            _v, briefs = MarketAnalystAgent().analyze(self.ctx.governance, symbols=wanted[:2])
            return "; ".join(f"{b.symbol} {b.price_usdt:.0f}$ ({b.change_24h_pct:+.1f}%, {b.trend})" for b in briefs)
        except Exception:
            return "marché indisponible (réseau)"

    def _t_library(self, arg: str) -> str:
        from ..integrations.library import OpenSourceLibrary
        hits = OpenSourceLibrary().search(arg or "", limit=3)
        return "; ".join(f"{h['full_name']} ({h['stars']}★)" for h in hits) or "aucun repo trouvé"

    # ---- la boucle ----
    def run(self, goal: str, granted: AutonomyLevel = AutonomyLevel.A1,
            max_steps: int = 5) -> dict[str, Any]:
        verdict = self.ctx.governance.submit(
            Action(type=ActionType.ANALYZE, actor=self.name, description=f"Raisonner : {goal[:60]}"),
            granted)
        if verdict.decision is not Decision.ALLOW:
            return {"decision": verdict.decision.value, "answer": None, "steps": []}

        tool_list = "\n".join(f"- {n}(arg) : {self._tool_hint(n)}" for n in self._tools)
        observations: list[str] = []
        steps: list[dict] = []
        cache: dict[tuple[str, str], str] = {}   # anti-répétition (efficacité + moins d'appels)

        for _ in range(max_steps):
            prompt = self._build_prompt(goal, tool_list, observations)
            try:
                raw = self.llm.complete(prompt, num_predict=200).strip()
            except Exception:
                break
            action = self._parse(raw)
            if action is None or "final" in action:
                answer = (action or {}).get("final") or raw
                return {"decision": "allow", "answer": answer, "steps": steps}
            tool = action.get("outil") or action.get("tool")
            arg = str(action.get("args") or action.get("arg") or "")
            fn = self._tools.get(tool)
            if fn is None:
                observations.append(f"[outil inconnu: {tool} — utilise la liste fournie]")
                continue
            key = (tool, arg)
            if key in cache:                      # déjà lu : ne pas re-solliciter, pousser à conclure
                observations.append(f"[{tool}({arg}) déjà obtenu — tu as de quoi conclure]")
                continue
            result = fn(arg)                      # lecture gouvernée (déjà sous A1)
            cache[key] = result
            self.ctx.governance.bus.emit("reasoning.tool", tool=tool)
            observations.append(f"{tool}({arg}) = {result}")
            steps.append({"tool": tool, "arg": arg, "result": result})

        # limite atteinte : on demande une synthèse finale des observations
        final = self._final_synthesis(goal, observations)
        return {"decision": "allow", "answer": final, "steps": steps}

    # ---- helpers ----
    _HINTS = {
        "portefeuille": "l'état des business", "tresorerie": "recettes/dépenses/solde",
        "prospection": "prospects et relances", "commandes": "ventes/achats à traiter",
        "marche": "prix crypto (arg=btc/eth)", "bibliotheque": "repos open-source locaux (arg=besoin)",
    }

    def _tool_hint(self, name: str) -> str:
        return self._HINTS.get(name, "")

    def _build_prompt(self, goal: str, tools: str, obs: list[str]) -> str:
        from ..persona import FOUNDER_PROMPT
        obs_txt = ("\nObservations déjà récoltées :\n" + "\n".join(obs)) if obs else ""
        return (
            f"{FOUNDER_PROMPT}\n\n"
            "Tu raisonnes pour atteindre l'objectif du fondateur. Tu peux LIRE tes outils.\n"
            f"Outils disponibles :\n{tools}\n"
            "Répertoire STRICT de réponse — un seul objet JSON, rien d'autre :\n"
            '  pour utiliser un outil : {\"outil\": \"nom\", \"args\": \"...\"}\n'
            '  pour conclure         : {\"final\": \"ta réponse en 80 mots max, ancrée dans les observations\"}\n'
            "N'invente aucun chiffre : sers-toi UNIQUEMENT des observations. "
            "Conclus dès que tu as de quoi répondre.\n"
            f"{obs_txt}\n\nObjectif : {goal}\nJSON :"
        )

    def _parse(self, raw: str) -> dict | None:
        m = re.search(r"\{.*\}", raw, re.S)
        if not m:
            return None
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            return None

    def _final_synthesis(self, goal: str, obs: list[str]) -> str:
        from ..persona import FOUNDER_PROMPT
        try:
            return self.llm.complete(
                f"{FOUNDER_PROMPT}\n\nÀ partir de ces observations RÉELLES :\n"
                + "\n".join(obs) +
                f"\n\nRéponds à l'objectif « {goal} » en 80 mots max, sans rien inventer, "
                "en terminant par LA priorité de la semaine.\nRéponse :", num_predict=220).strip()
        except Exception:
            return "Observations : " + " | ".join(obs)

    def propose(self, context: dict[str, Any]) -> Action:
        return Action(type=ActionType.ANALYZE, actor=self.name,
                      description=f"Raisonner : {context.get('goal', '')[:60]}")
