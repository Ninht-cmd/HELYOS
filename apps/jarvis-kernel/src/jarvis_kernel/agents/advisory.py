"""Le Comité — l'équipe C-suite du PROMPT MASTER, en CONSEILLERS gouvernés.

Le prompt demandait des agents CEO/CFO/CTO/CMO… « autonomes » qui exécutent.
La vérité de gouvernance : un agent qui dépense, signe ou trade en autonomie
viole GR-7/GR-2. Donc ici, chaque C-level est un CONSEILLER (A1) : il analyse
sous son angle, ancré dans l'état RÉEL de tes business (portefeuille, caisse,
prospection), et il RECOMMANDE. L'exécution reste humaine et gouvernée.

C'est le bon usage de l'IA : douze angles d'expertise sur ta situation réelle,
en une question — pas douze robots lâchés sur ton compte en banque.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..governance.autonomy import AutonomyLevel
from ..governance.policy import Action, ActionType, Decision
from ..governance.service import GovernanceService
from .base import Agent
from .llm import LLMPort, StubLLM


@dataclass(frozen=True)
class Role:
    key: str
    title: str
    lens: str          # l'angle unique de ce conseiller (injecté dans le prompt)


# Les douze angles du PROMPT MASTER — chacun conseille, aucun n'exécute.
ROLES: dict[str, Role] = {
    r.key: r for r in [
        Role("ceo", "Directeur général", "stratégie, priorités, quelle bataille livrer maintenant et laquelle refuser"),
        Role("cfo", "Directeur financier", "trésorerie réelle, coûts, ROI, ce qui rapproche ou éloigne du premier euro — jamais promettre un revenu"),
        Role("cto", "Directeur technique", "architecture, dette technique, ne pas réinventer ce qui existe (assembler l'open source)"),
        Role("coo", "Directeur des opérations", "processus, ce qui est répétable, ce qu'on peut automatiser sans casser la gouvernance"),
        Role("cmo", "Directeur marketing", "acquisition sans démarchage sortant, contenu, la vitrine, ce qui fait venir les acheteurs"),
        Role("sales", "Directeur commercial", "convertir l'intérêt en paiement, l'offre, l'objection à lever, le prochain oui"),
        Role("support", "Directeur client", "satisfaction, ce qui fait revenir un client, le premier témoignage"),
        Role("rh", "Directeur RH", "compétences manquantes, quand déléguer/sous-traiter vs faire soi-même"),
        Role("legal", "Directeur juridique", "conformité FR (micro-entreprise, RGPD, CGV), risques — pas un avis juridique, orienter vers un pro"),
        Role("ciso", "Directeur sécurité", "risques data/sécurité, ce qui protège avant d'exposer (auth avant public)"),
        Role("data", "Directeur data", "les 3 chiffres qui comptent cette semaine, ce que les données réelles disent"),
        Role("research", "Directeur recherche", "veille, opportunités, ce qui existe déjà à réutiliser"),
    ]
}

# alias langage naturel -> clé de rôle
_ALIASES = {
    "pdg": "ceo", "directeur general": "ceo", "strateg": "ceo",
    "financ": "cfo", "argent": "cfo", "tresorerie": "cfo", "budget": "cfo",
    "techniq": "cto", "code": "cto", "archi": "cto",
    "operation": "coo", "process": "coo",
    "marketing": "cmo", "acquisition": "cmo", "communication": "cmo",
    "vente": "sales", "commercial": "sales", "closing": "sales",
    "support": "support", "client": "support", "satisfaction": "support",
    "recrut": "rh", "competence": "rh", "delegu": "rh",
    "juridiq": "legal", "droit": "legal", "conformit": "legal", "rgpd": "legal",
    "securit": "ciso", "cyber": "ciso", "menace": "ciso",
    "donnee": "data", "kpi": "data", "chiffre": "data", "metriqu": "data",
    "recherche": "research", "veille": "research", "innovation": "research",
}


class AdvisoryBoard(Agent):
    name = "advisory_board"
    description = ("Comité C-suite (CEO, CFO, CTO, CMO…) en conseillers gouvernés A1 : "
                   "analysent ta situation RÉELLE et recommandent. N'exécutent jamais.")
    required_level = AutonomyLevel.A1

    def __init__(self, llm: LLMPort | None = None) -> None:
        self.llm = llm or StubLLM()

    def propose(self, context: dict[str, Any]) -> Action:
        return Action(type=ActionType.ANALYZE, actor=self.name,
                      description=f"Conseil {context.get('role', 'comité')} : {context.get('q', '')[:60]}")

    @staticmethod
    def pick_role(message: str) -> Role | None:
        """Rôle explicitement demandé dans la phrase, sinon None (=> le CEO synthétise).

        Insensible aux accents : « sécurité » doit matcher l'alias « securit »."""
        import unicodedata

        m = "".join(c for c in unicodedata.normalize("NFD", message.lower())
                    if unicodedata.category(c) != "Mn")
        for key in ROLES:
            if key in m:
                return ROLES[key]
        for alias, key in _ALIASES.items():
            if alias in m:
                return ROLES[key]
        return None

    def _state(self, ctx) -> str:
        """Ancrage : l'état RÉEL de la holding, pour un conseil situé et pas générique."""
        lines = []
        try:
            g = ctx.ledger.global_summary() if ctx.ledger else {"solde_eur": 0, "recettes_eur": 0}
            lines.append(f"Caisse : {g.get('recettes_eur', 0):.0f} € encaissés, solde {g.get('solde_eur', 0):.0f} €.")
        except Exception:
            pass
        try:
            biz = ctx.portfolio.list()
            lines.append(f"Portefeuille : {len(biz)} business ({', '.join(b.name.split(' (')[0] for b in biz[:4])}).")
        except Exception:
            pass
        try:
            from ..business.prospection import ProspectionPipeline
            s = ProspectionPipeline(ctx.memory).stats()
            lines.append(f"Prospection : {s['total']} prospects, {s['clients']} client(s).")
        except Exception:
            pass
        return " ".join(lines) or "État non disponible."

    def advise(self, ctx, governance: GovernanceService, message: str,
               granted: AutonomyLevel = AutonomyLevel.A1) -> tuple[Any, dict | None]:
        role = self.pick_role(message) or ROLES["ceo"]
        verdict = governance.submit(self.propose({"role": role.key, "q": message}), granted)
        if verdict.decision is not Decision.ALLOW:
            return verdict, None

        from ..persona import FOUNDER_PROMPT
        state = self._state(ctx)
        prompt = (
            f"{FOUNDER_PROMPT}\n\n"
            f"Tu réponds ici en tant que {role.title} d'HELYOS. Ton angle : {role.lens}.\n"
            f"État réel de la holding : {state}\n"
            "Règles : prose simple (pas de titres ni listes), 100 mots max, "
            "ancré dans l'état réel ci-dessus, jamais de chiffre inventé ni de revenu promis. "
            "Termine par UNE action concrète que le fondateur peut faire cette semaine.\n\n"
            f"Question du fondateur : {message}\nRéponse du {role.title} :"
        )
        try:
            text = self.llm.complete(prompt, num_predict=240).strip()
        except Exception:
            text = ""
        if not text or "Tu réponds ici" in text:
            text = (f"[{role.title}] Il me faut le modèle local (Ollama) connecté pour "
                    "un conseil argumenté. Sans lui, je m'en tiens aux actions gouvernées.")
        return verdict, {"role": role.key, "title": role.title, "text": text}
