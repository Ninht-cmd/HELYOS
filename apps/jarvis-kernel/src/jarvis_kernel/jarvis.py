"""Jarvis — l'intelligence conversationnelle qui UNIFIE HELYOS.

Le « moment Jarvis » honnête : tu parles en langage naturel, HELYOS comprend l'intention,
route vers la bonne capacité (factures, business, portefeuille, recherche, gouvernance),
AGIT sous gouvernance A0–A5, et répond. Une seule intelligence, pas des agents épars.

Ce n'est pas de la magie : la compréhension = classification d'intention (LLM réel si
dispo, sinon règles déterministes) ; l'action = les agents déjà construits et testés ;
et toute action sur le monde reste gouvernée (le refus fait partie de la réponse).
"""

from __future__ import annotations

import re
import threading
from dataclasses import dataclass

from .agents.business_scaffolder import BusinessScaffolder
from .agents.invoice_reminder import Invoice, InvoiceReminderAgent
from .agents.llm import LLMPort, StubLLM
from .agents.research import ResearchAgent
from .context import KernelContext
from .governance.autonomy import AutonomyLevel
from .governance.policy import Action, ActionType, Decision
from .observability.tracing import span

# Intentions reconnues. La classification renvoie l'une de ces étiquettes.
INTENTS = ("portefeuille", "prospection", "relance_factures", "creer_business", "recherche",
           "marche_financier", "simulation_trading", "action_dangereuse", "conversation")

# Filet déterministe (marche sans LLM). Motifs verbe/sujet, pas simples mots-clés.
# ORDRE VOLONTAIRE : les actions dangereuses sont testées EN PREMIER — « supprime mes
# factures » doit déclencher la gouvernance, pas la rédaction de relances.
_RULES: list[tuple[str, str]] = [
    # « paie(?!ment) » : « paie la facture » = financier, mais « paiement en retard »
    # appartient au flux factures — sinon la relance serait détournée vers la gouvernance.
    ("action_dangereuse", r"supprim|efface|d[ée]truis|vire?ment|paie(?!ment)|transf[eè]re|ach[eè]te|vends|investis|donne.{0,10}droit|permission|privil[eè]g"),
    ("portefeuille", r"portefeuille|mes business|mes affaires|o[uù] en (est|sont)|statut|tableau de bord|r[ée]capitulatif"),
    # AVANT factures : « qui dois-je relancer » (prospects) ≠ « relance mes factures »
    ("prospection", r"prospect|pipeline|d[ée]marchage|qui dois-je relancer"),
    ("relance_factures", r"factur|relance|impay|client.{0,10}doit|paiement.{0,15}retard|retard.{0,15}paiement"),
    ("creer_business", r"cr[ée]e.{0,15}business|nouvelle boutique|lance.{0,15}(business|boutique)|scaffold"),
    # la simulation (argent fictif) se distingue du marché réel et des ordres réels
    ("simulation_trading", r"simul|fictif|virtuel|paper.?trad"),
    # « marché » seul reste une étude de marché (recherche) ; la finance exige son lexique.
    ("marche_financier", r"bourse|crypto|bitcoin|\bbtc\b|ethereum|\beth\b|solana|trading|cours d[eu]|march[ée].{0,12}(financ|boursier)"),
    ("recherche", r"recherche|analyse|r[ée]sume|[ée]tudie|veille|renseigne"),
]


@dataclass(frozen=True)
class JarvisReply:
    intent: str
    text: str
    governed: bool = False        # une décision de gouvernance a-t-elle eu lieu ?
    decision: str | None = None   # allow / require_validation / deny
    rule: str | None = None


class Jarvis:
    """Point d'entrée conversationnel unique de HELYOS."""

    def __init__(self, ctx: KernelContext, llm: LLMPort | None = None) -> None:
        self.ctx = ctx
        self.llm = llm or StubLLM(prefix="[jarvis]")
        self._mem_lock = threading.Lock()   # deux requêtes concurrentes ≠ un échange perdu

    # --- compréhension ---
    def classify(self, message: str) -> str:
        """Règles d'abord (déterministe, testable) ; LLM en tie-breaker si ambigu.

        Les règles tranchent la majorité des cas sans réseau. Seulement quand elles
        retombent sur « conversation » on interroge le LLM — et on ne fait confiance
        qu'à une réponse COURTE (une vraie étiquette fait < 40 caractères ; un écho de
        prompt, non), ce qui neutralise le StubLLM qui recopie l'énoncé.
        """
        intent = self._classify_rules(message)
        if intent != "conversation":
            return intent
        return self._classify_llm(message) or "conversation"

    def _classify_rules(self, message: str) -> str:
        m = message.lower()
        for intent, pattern in _RULES:
            if re.search(pattern, m):
                return intent
        return "conversation"

    def _classify_llm(self, message: str) -> str:
        prompt = (
            "Classe l'intention de ce message dans EXACTEMENT une de ces étiquettes "
            f"(réponds par le seul mot) : {', '.join(INTENTS)}.\n"
            "Règle : une question de suivi, une question sur HELYOS lui-même, ou un message "
            "trop vague pour être étudié = conversation (pas recherche).\n"
            f"Message : \"{message}\"\nÉtiquette :"
        )
        try:
            out = self.llm.complete(prompt, num_predict=8).strip().lower()
        except Exception:
            return ""
        if len(out) > 40:            # rejet d'un écho de prompt (StubLLM) : une étiquette est courte
            return ""
        for intent in INTENTS:
            if intent in out:
                return intent
        return ""

    # --- mémoire de conversation (un Jarvis se souvient de ce qu'on s'est dit) ---
    _THREAD_MAX = 24   # entrées conservées (12 échanges) — assez pour la continuité, pas un log

    def history(self) -> list[dict]:
        return list(self.ctx.memory.recall("thread", namespace="conversation") or [])

    def _remember_exchange(self, message: str, reply: JarvisReply) -> None:
        with self._mem_lock:                # lecture-ajout-écriture atomique
            thread = self.history()
            thread.append({"role": "fondateur", "text": message[:500], "intent": None})
            thread.append({"role": "helyos", "text": reply.text[:800], "intent": reply.intent})
            self.ctx.memory.remember("thread", thread[-self._THREAD_MAX:],
                                     namespace="conversation")

    # --- action (sous gouvernance) ---
    def handle(self, message: str, granted: AutonomyLevel = AutonomyLevel.A1) -> JarvisReply:
        with span("jarvis.handle", **{"helyos.msg": message[:60]}):
            intent = self.classify(message)
            if intent == "portefeuille":
                reply = self._portfolio()
            elif intent == "prospection":
                reply = self._prospection(message)
            elif intent == "relance_factures":
                reply = self._invoices(granted)
            elif intent == "creer_business":
                reply = self._business(message, granted)
            elif intent == "recherche":
                reply = self._research(message, granted)
            elif intent == "marche_financier":
                reply = self._market(message, granted)
            elif intent == "simulation_trading":
                reply = self._paper(granted)
            elif intent == "action_dangereuse":
                reply = self._dangerous(message, granted)
            else:
                reply = self._talk(message)
            try:
                self._remember_exchange(message, reply)
            except Exception:      # la mémoire ne doit jamais casser la réponse…
                from .observability.telemetry import get_logger
                get_logger(__name__).warning("mémoire de conversation en échec")  # …ni se perdre en silence
            return reply

    def _portfolio(self) -> JarvisReply:
        items = self.ctx.portfolio.summary()
        if not items:
            return JarvisReply("portefeuille", "Ton portefeuille est vide pour l'instant.")
        lines = [f"Je gère {len(items)} business :"]
        for b in items:
            lines.append(f"  • {b['name']} — {b['status']} ({b['open_tasks']} tâche(s) ouverte(s))")
        return JarvisReply("portefeuille", "\n".join(lines))

    def _invoices(self, granted: AutonomyLevel) -> JarvisReply:
        stored = self.ctx.memory.recall("factures_impayees", namespace="factures")
        if not stored:
            return JarvisReply("relance_factures",
                "Donne-moi la liste des factures impayées (client, montant, jours de retard) "
                "et je rédige les relances — tu valideras avant tout envoi.")
        agent = InvoiceReminderAgent(llm=self.llm)
        invoices = [Invoice(**d) for d in stored]
        v, reminders = agent.draft_reminders(self.ctx.governance, invoices, granted=granted,
                                             memory=self.ctx.memory)
        if v.decision is not Decision.ALLOW:
            return JarvisReply("relance_factures",
                "Je peux les préparer, mais il me faut le niveau A1.", True, v.decision.value, v.rule)
        return JarvisReply("relance_factures",
            f"J'ai rédigé {len(reminders)} relance(s). Rien n'est envoyé : tu valides d'abord "
            "chaque e-mail (règle d'or GR-2).", True, v.decision.value)

    def _business(self, message: str, granted: AutonomyLevel) -> JarvisReply:
        agent = BusinessScaffolder(llm=self.llm)
        # Nom dérivé de la demande : deux créations successives ne s'écrasent pas en mémoire.
        name = f"Business — {message.strip()[:48]}" if message.strip() else "Nouveau business"
        v, plan = agent.scaffold(self.ctx.governance, name=name,
                                 niche=message, granted=granted, memory=self.ctx.memory)
        if plan is None:
            return JarvisReply("creer_business",
                "Il me faut le niveau A1 pour préparer un business.", True, v.decision.value, v.rule)
        return JarvisReply("creer_business",
            f"J'ai scaffolder un business ({len(plan.products)} produits, {len(plan.required_pages)} "
            "pages). Le publier sur une plateforme réelle exigera ta validation.", True, v.decision.value)

    def _research(self, message: str, granted: AutonomyLevel) -> JarvisReply:
        agent = ResearchAgent(llm=self.llm)
        v, finding = agent.analyze(self.ctx.governance, message, granted=granted, memory=self.ctx.memory)
        if finding is None:
            return JarvisReply("recherche", "Il me faut le niveau A1 pour analyser.",
                               True, v.decision.value, v.rule)
        return JarvisReply("recherche", finding, True, v.decision.value)

    def _market(self, message: str, granted: AutonomyLevel) -> JarvisReply:
        from .agents.market_analyst import DEFAULT_SYMBOLS, SYMBOLS, MarketAnalystAgent

        m = message.lower()
        wanted = tuple(dict.fromkeys(pair for word, pair in SYMBOLS.items() if word in m)) \
            or DEFAULT_SYMBOLS
        agent = MarketAnalystAgent()
        try:
            v, briefs = agent.analyze(self.ctx.governance, symbols=wanted, granted=granted)
        except Exception:                     # réseau coupé : on le dit, on n'invente rien
            return JarvisReply("marche_financier",
                "Impossible de lire le marché (réseau ou API indisponible). "
                "Je n'invente jamais un prix — réessaie plus tard.")
        if not briefs:
            return JarvisReply("marche_financier",
                "Il me faut le niveau A1 pour analyser le marché.",
                True, v.decision.value, v.rule)
        txt = (agent.summary_text(briefs)
               + "\n\nSi tu veux une proposition d'ordre, demande-la : elle exigera ta "
                 "validation (GR-7) — et aucun courtier n'est branché, donc je prépare, "
                 "tu exécutes.")
        return JarvisReply("marche_financier", txt, True, v.decision.value)

    def _prospection(self, message: str) -> JarvisReply:
        from .business.prospection import ProspectionPipeline

        pipe = ProspectionPipeline(self.ctx.memory)
        m = re.search(r"ajoute\s+(?:un\s+)?prospect\s*[:\-]\s*(.+)", message, re.IGNORECASE)
        if m:
            parts = [x.strip() for x in m.group(1).split(",")]
            p = pipe.add(parts[0], company=parts[1] if len(parts) > 1 else "",
                         contact=parts[2] if len(parts) > 2 else "")
            draft = pipe.draft_outreach(self.llm, p)
            return JarvisReply("prospection",
                f"Prospect ajouté : {p.name}" + (f" ({p.company})" if p.company else "") +
                f". Brouillon de premier contact :\n\n{draft}\n\n"
                "Rien n'est envoyé : tu copies/adaptes, ou tu branches SMTP pour un envoi "
                "gouverné (GR-2). Marque-le « contacté » quand c'est fait — je te rappellerai "
                "la relance à J+3.")
        s = pipe.stats()
        if s["total"] == 0:
            return JarvisReply("prospection",
                "Pipeline vide. Dis-moi : « ajoute un prospect : Nom, Société, contact » — "
                "je rédige le premier message. Objectif Plan Cash : 20 contacts/semaine.")
        due = pipe.due_followups()
        lines = [f"Pipeline : {s['total']} prospect(s) — {s['contactes']} contacté(s), "
                 f"{s['reponses']} réponse(s), {s['clients']} client(s)."]
        if due:
            lines.append(f"À relancer maintenant ({len(due)}) : "
                         + ", ".join(f"{p.name} ({next_s})" for p, next_s in due[:5]))
        else:
            lines.append("Aucune relance due — le rythme J+3/J+7 est tenu.")
        return JarvisReply("prospection", "\n".join(lines))

    def _paper(self, granted: AutonomyLevel) -> JarvisReply:
        from .agents.paper_trader import PaperTrader

        agent = PaperTrader()
        try:
            v, s = agent.step(self.ctx.governance, self.ctx.memory, granted=granted)
        except Exception:
            return JarvisReply("simulation_trading",
                "Impossible de lire les prix (réseau/API indisponible) — la simulation "
                "attend, je n'invente pas un cours.")
        if s is None:
            return JarvisReply("simulation_trading",
                "Il me faut le niveau A1 pour faire tourner la simulation.",
                True, v.decision.value, v.rule)
        pos = ", ".join(f"{k} {float(q):.6f}" for k, q in s["positions"].items()) or "aucune"
        text = (f"Simulation de trading — ARGENT FICTIF, prix réels :\n"
                f"  • Capital virtuel : {s['equity_eur']:.2f} € ({s['pnl_pct']:+.2f} % "
                f"depuis {s['start_eur']:.0f} €) · liquidités {s['cash_eur']:.2f} €\n"
                f"  • Positions : {pos} · {s['executed']} ordre(s) virtuel(s) ce tour, "
                f"{s['trades_count']} au total\n"
                "Aucun euro réel n'est engagé. C'est le banc d'essai : si cette stratégie "
                "ne bat pas le simple fait de garder l'argent, elle ne touchera jamais un "
                "euro réel — et même prouvée, chaque ordre réel exigera ta validation (GR-7).")
        return JarvisReply("simulation_trading", text, True, v.decision.value)

    def _dangerous(self, message: str, granted: AutonomyLevel) -> JarvisReply:
        """Une demande d'action risquée : on la SOUMET à la gouvernance et on répond avec le verdict."""
        m = message.lower()
        if re.search(r"vire?ment|paie(?!ment)|transf[eè]re|ach[eè]te|vends|investis", m):
            atype = ActionType.FINANCIAL
        elif re.search(r"droit|permission|privil[eè]g", m):
            atype = ActionType.SELF_PERMISSION
        else:
            atype = ActionType.DELETE
        action = Action(type=atype, description=message, actor="jarvis")
        v = self.ctx.governance.submit(action, granted)
        if v.decision is Decision.DENY:
            txt = f"Non, je ne le fais pas. {v.reason}"
        elif v.decision is Decision.REQUIRE_VALIDATION:
            txt = f"Je peux le préparer, mais ça exige ta validation explicite. {v.reason}"
        else:
            txt = "C'est autorisé à ton niveau — je peux procéder."
        return JarvisReply("action_dangereuse", txt, True, v.decision.value, v.rule)

    def _talk(self, message: str) -> JarvisReply:
        from .persona import FOUNDER_PROMPT

        # continuité : les derniers échanges entrent dans le prompt (court : LLM local).
        # Retours à la ligne aplatis : un texte mémorisé ne doit pas pouvoir se faire
        # passer pour une nouvelle ligne d'instruction du prompt.
        recent = self.history()[-6:]
        memo = "".join(
            f"\n{'Fondateur' if e['role'] == 'fondateur' else 'HELYOS'} : "
            f"{e['text'][:200].replace(chr(10), ' ')}"
            for e in recent)
        context_block = f"\n\nDerniers échanges :{memo}" if memo else ""
        try:
            reply = self.llm.complete(
                f"{FOUNDER_PROMPT}{context_block}\n\nMessage du fondateur : \"{message}\"\nRéponse :").strip()
        except Exception:                     # Ollama éteint / réseau : on reste debout
            reply = ""
        if not reply or "Tu es HELYOS" in reply:   # vide ou écho du StubLLM : repli honnête
            reply = ("Je suis HELYOS — intelligence gouvernée, locale d'abord. Sans modèle "
                     "local connecté (Ollama), je réponds surtout aux actions : portefeuille, "
                     "factures, business, recherche.")
        return JarvisReply("conversation", reply)


def build_jarvis(ctx: KernelContext | None = None) -> Jarvis:
    """Construit (ou réutilise) un Jarvis avec le même backend LLM que le contexte.

    Local First : StubLLM par défaut ; OllamaLLM si ``HELYOS_LLM_BACKEND=ollama``.
    """
    from .context import build_default_context

    ctx = ctx or build_default_context()
    if isinstance(ctx.jarvis, Jarvis):        # déjà câblé par build_default_context
        return ctx.jarvis
    return Jarvis(ctx, llm=ctx.llm or StubLLM(prefix="[jarvis]"))
