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
        self._granted = AutonomyLevel.A1
        self._tools: dict[str, Callable[[str], str]] = {
            # --- LECTURE (A1) : observer ---
            "portefeuille": self._t_portfolio,
            "tresorerie": self._t_treasury,
            "prospection": self._t_prospection,
            "commandes": self._t_orders,
            "marche": self._t_market,
            "bibliotheque": self._t_library,
            # --- ACTION (interne, réversible ; exige A2) : agir ---
            "enregistre_recette": self._a_recette,
            "enregistre_depense": self._a_depense,
            "ajoute_prospect": self._a_prospect,
            "coche_tache": self._a_tache,
            "nouvelle_commande": self._a_commande,
            "nouvelle_tache": self._a_nouvelle_tache,
            "active_module": self._a_active_module,
            "note_memoire": self._a_note,
        }
        self._actions = {"enregistre_recette", "enregistre_depense", "ajoute_prospect",
                         "coche_tache", "nouvelle_commande", "nouvelle_tache",
                         "active_module", "note_memoire"}

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

    # ---- outils d'ACTION (interne, réversible ; passent par la gouvernance : A2 requis) ----
    def _gate(self, atype: ActionType, desc: str) -> bool:
        """Toute action réelle est soumise. Écriture interne = A2 ; en A1 : refus honnête."""
        v = self.ctx.governance.submit(
            Action(type=atype, actor=self.name, description=desc), self._granted)
        return v.decision is Decision.ALLOW

    def _match_business(self, text: str) -> str | None:
        t = (text or "").lower()
        best, score = None, 0
        for b in self.ctx.portfolio.list():
            toks = [w for w in re.split(r"[^\wéèà-]+", b.name.lower()) if len(w) > 3]
            s = sum(1 for w in toks if w in t)
            if s > score:
                best, score = b.name, s
        return best

    @staticmethod
    def _amount(text: str) -> float:
        m = re.search(r"(\d+(?:[.,]\d+)?)", text or "")
        return float(m.group(1).replace(",", ".")) if m else 0.0

    def _a_recette(self, arg: str) -> str:
        biz, amt = self._match_business(arg), self._amount(arg)
        if not biz or amt <= 0:
            return "[besoin d'un business et d'un montant > 0]"
        if not self._gate(ActionType.WRITE_LOCAL, f"enregistrer recette {amt}€ / {biz}"):
            return "[refusé : lève l'autonomie à A2 pour que j'agisse]"
        self.ctx.ledger.add(biz, "recette", amt, "cerveau")
        return f"recette {amt:.2f}€ enregistrée pour {biz}"

    def _a_depense(self, arg: str) -> str:
        biz, amt = self._match_business(arg), self._amount(arg)
        if not biz or amt <= 0:
            return "[besoin d'un business et d'un montant > 0]"
        if not self._gate(ActionType.WRITE_LOCAL, f"enregistrer dépense {amt}€ / {biz}"):
            return "[refusé : lève l'autonomie à A2 pour que j'agisse]"
        self.ctx.ledger.add(biz, "depense", amt, "cerveau")
        return f"dépense {amt:.2f}€ enregistrée pour {biz}"

    def _a_prospect(self, arg: str) -> str:
        nom = (arg or "").split(",")[0].strip()
        if len(nom) < 2:
            return "[besoin d'un nom de prospect]"
        if not self._gate(ActionType.WRITE_LOCAL, f"ajouter prospect {nom}"):
            return "[refusé : lève l'autonomie à A2 pour que j'agisse]"
        from ..business.prospection import ProspectionPipeline
        ProspectionPipeline(self.ctx.memory).add(nom)
        return f"prospect « {nom} » ajouté au pipeline"

    def _a_tache(self, arg: str) -> str:
        biz = self._match_business(arg)
        if not biz:
            return "[besoin de préciser le business]"
        if not self._gate(ActionType.WRITE_LOCAL, f"cocher une tâche / {biz}"):
            return "[refusé : lève l'autonomie à A2 pour que j'agisse]"
        # coche la 1re tâche ouverte du business (réversible)
        b = self.ctx.portfolio.get(biz)
        opens = [t for t in (b.tasks if b else []) if not t.get("done")]
        if not opens:
            return f"aucune tâche ouverte sur {biz}"
        self.ctx.portfolio.complete_task(biz, opens[0]["task"][:30])
        return f"tâche cochée sur {biz} : {opens[0]['task'][:50]}"

    def _a_commande(self, arg: str) -> str:
        amt = self._amount(arg)
        sens = "achat" if re.search(r"\bachat\b|fournisseur", (arg or "").lower()) else "vente"
        partie = re.sub(r"\d+(?:[.,]\d+)?|\b(vente|achat|fournisseur|client|€|euros?)\b",
                        "", arg or "", flags=re.IGNORECASE).strip(" ,-") or "?"
        if amt <= 0:
            return "[besoin d'un montant > 0]"
        if not self._gate(ActionType.WRITE_LOCAL, f"nouvelle {sens} {amt}€ / {partie}"):
            return "[refusé : lève l'autonomie à A2 pour que j'agisse]"
        from ..business.orders import OrderBook
        o = OrderBook(self.ctx.memory).add(sens, partie, "", amt)
        return f"{sens} de {amt:.2f}€ enregistrée ({partie}, réf {o.id})"

    def _a_nouvelle_tache(self, arg: str) -> str:
        parts = re.split(r"[:|]", arg or "", maxsplit=1)
        biz = self._match_business(parts[0]) or self._match_business(arg)
        texte = (parts[1] if len(parts) > 1 else arg).strip()
        if not biz or len(texte) < 3:
            return "[besoin d'un business et d'un intitulé de tâche]"
        if not self._gate(ActionType.WRITE_LOCAL, f"ajouter tâche / {biz}"):
            return "[refusé : lève l'autonomie à A2 pour que j'agisse]"
        self.ctx.portfolio.add_task(biz, f"[HELYOS] {texte[:80]}", owner="helyos")
        return f"tâche ajoutée sur {biz} : {texte[:60]}"

    def _a_active_module(self, arg: str) -> str:
        from ..integrations.modules import DEFAULTS, ModuleRegistry
        a = (arg or "").lower()
        target = next((m for m in DEFAULTS if m.key in a or m.name.lower().split(" (")[0] in a), None)
        if target is None:
            return "[module non reconnu]"
        if not self._gate(ActionType.WRITE_LOCAL, f"activer module {target.key}"):
            return "[refusé : lève l'autonomie à A2 pour que j'agisse]"
        ModuleRegistry(self.ctx.memory).toggle(target.key, True)
        return f"module « {target.name} » activé"

    def _a_note(self, arg: str) -> str:
        note = (arg or "").strip()
        if len(note) < 3:
            return "[note vide]"
        if not self._gate(ActionType.WRITE_LOCAL, "noter en mémoire"):
            return "[refusé : lève l'autonomie à A2 pour que j'agisse]"
        import time
        notes = list(self.ctx.memory.recall("notes", namespace="brain") or [])
        notes.append({"note": note[:200], "ts": time.time()})
        self.ctx.memory.remember("notes", notes[-50:], namespace="brain")
        return f"noté : {note[:60]}"

    # ---- la boucle ----
    def run(self, goal: str, granted: AutonomyLevel = AutonomyLevel.A1,
            max_steps: int = 6) -> dict[str, Any]:
        self._granted = granted
        verdict = self.ctx.governance.submit(
            Action(type=ActionType.ANALYZE, actor=self.name, description=f"Raisonner : {goal[:60]}"),
            granted)
        if verdict.decision is not Decision.ALLOW:
            return {"decision": verdict.decision.value, "answer": None, "steps": []}

        def line(n: str) -> str:
            tag = " [ACTION, A2]" if n in self._actions else ""
            return f"- {n}(arg) : {self._tool_hint(n)}{tag}"
        tool_list = "\n".join(line(n) for n in self._tools)
        observations: list[str] = []
        steps: list[dict] = []
        cache: dict[tuple[str, str], str] = {}   # anti-répétition (efficacité + moins d'appels)

        for _ in range(max_steps):
            prompt = self._build_prompt(goal, tool_list, observations)
            try:
                raw = self.llm.complete(prompt, num_predict=260).strip()
            except Exception:
                break
            objs = self._json_objects(raw)
            if not objs:                          # rien de parsable : c'est la réponse finale
                return {"decision": "allow", "answer": raw, "steps": steps}
            # le modèle peut émettre PLUSIEURS actions d'un coup : on les exécute toutes,
            # dans l'ordre, jusqu'à un {"final"} (vécu en lancement réel : qwen3 batch).
            progressed = False
            for action in objs:
                if "final" in action:
                    return {"decision": "allow", "answer": action["final"], "steps": steps}
                tool = action.get("outil") or action.get("tool")
                arg = str(action.get("args") or action.get("arg") or "")
                fn = self._tools.get(tool)
                if fn is None:
                    observations.append(f"[outil inconnu: {tool}]")
                    continue
                key = (tool, arg)
                if key in cache:
                    observations.append(f"[{tool}({arg}) déjà fait]")
                    continue
                result = fn(arg)                  # lecture (A1) ou action (gouvernée, A2)
                cache[key] = result
                progressed = True
                self.ctx.governance.bus.emit("reasoning.tool", tool=tool)
                observations.append(f"{tool}({arg}) = {result}")
                steps.append({"tool": tool, "arg": arg, "result": result,
                              "is_action": tool in self._actions})
            _ = progressed   # on re-sollicite le modèle (il voit les observations et conclut) ;
            #                  la limite max_steps borne toute boucle, pas besoin de couper ici

        # limite atteinte : on demande une synthèse finale des observations
        final = self._final_synthesis(goal, observations)
        return {"decision": "allow", "answer": final, "steps": steps}

    # ---- helpers ----
    _HINTS = {
        "portefeuille": "l'état des business", "tresorerie": "recettes/dépenses/solde",
        "prospection": "prospects et relances", "commandes": "ventes/achats à traiter",
        "marche": "prix crypto (arg=btc/eth)", "bibliotheque": "repos open-source locaux (arg=besoin)",
        "enregistre_recette": "note une recette réelle (arg='business montant')",
        "enregistre_depense": "note une dépense (arg='business montant')",
        "ajoute_prospect": "ajoute un prospect (arg='nom')",
        "coche_tache": "coche une tâche faite (arg='business')",
        "nouvelle_commande": "enregistre une vente/achat (arg='client montant')",
        "nouvelle_tache": "ajoute une tâche (arg='business : intitulé')",
        "active_module": "allume un module/outil (arg='nom')",
        "note_memoire": "mémorise une note (arg='texte')",
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
            "Les outils [ACTION, A2] MODIFIENT l'état réel — ne les utilise QUE si "
            "l'objectif demande explicitement d'agir, et jamais pour de l'argent sortant.\n"
            "Répertoire STRICT de réponse — un seul objet JSON, rien d'autre :\n"
            '  pour utiliser un outil : {\"outil\": \"nom\", \"args\": \"...\"}\n'
            '  pour conclure         : {\"final\": \"ta réponse en 80 mots max, ancrée dans les observations\"}\n'
            "N'invente aucun chiffre : sers-toi UNIQUEMENT des observations. "
            "Conclus dès que tu as de quoi répondre.\n"
            f"{obs_txt}\n\nObjectif : {goal}\nJSON :"
        )

    def _json_objects(self, raw: str) -> list[dict]:
        """Extrait TOUS les objets JSON de haut niveau (scanner d'accolades, tolère
        plusieurs objets à la suite et le texte autour). Robuste au batch du modèle."""
        objs: list[dict] = []
        depth = 0
        start: int | None = None
        in_str = esc = False
        for i, c in enumerate(raw):
            if in_str:
                if esc:
                    esc = False
                elif c == "\\":
                    esc = True
                elif c == '"':
                    in_str = False
                continue
            if c == '"':
                in_str = True
            elif c == "{":
                if depth == 0:
                    start = i
                depth += 1
            elif c == "}":
                if depth > 0:
                    depth -= 1
                    if depth == 0 and start is not None:
                        try:
                            objs.append(json.loads(raw[start:i + 1]))
                        except json.JSONDecodeError:
                            pass
                        start = None
        return objs

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
