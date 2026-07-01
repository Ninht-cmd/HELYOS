"""ReclassifierGate — ferme les SOUS-DÉCLARATIONS de type par le contenu (Phase 2).

Problème (banc adverse) : un agent soumet une action nuisible sous un type anodin
(escalade en `write_local`, paiement en `write_local`, exfiltration en `analyze`,
suppression en `rename_workdir`). Le moteur ne juge que le type déclaré → fuite.

Correctif : détecter dans la description/cible une **intention d'action nuisible**
(verbe + objet, pas simple mot-clé) et **remonter** le type effectif au plus nuisible
détecté. Le moteur applique alors la bonne règle d'or.

Choix de conception honnête :
- On matche des **patrons verbe→objet** (« modifier mes permissions », « ordre de virement »),
  PAS le nom seul (« la procédure de suppression », « l'historique des virements ») : sinon on
  sur-bloquerait des actions honnêtes qui *mentionnent* le mot. Mesuré sur un jeu honnête
  porteur du lexique (faux positifs).
- **Limite assumée** : approche LEXICALE → vulnérable à la paraphrase. Le banc Phase 3 le
  démontre (variantes qui contournent). Fermer la classe → embedder/classifieur appris
  (question de recherche 2, RESET.md). On ne prétend donc PAS « classe fermée ».
"""

from __future__ import annotations

import dataclasses
import re
import unicodedata

from .policy import Action, ActionType


def _norm(s: str) -> str:
    d = unicodedata.normalize("NFD", (s or "").lower())
    return "".join(c for c in d if unicodedata.category(c) != "Mn")


# Rang de nocivité : on ne remonte JAMAIS vers moins nuisible.
_RANK = {
    ActionType.READ: 0, ActionType.ANALYZE: 1, ActionType.WRITE_LOCAL: 2,
    ActionType.RENAME_WORKDIR: 2, ActionType.EXTERNAL_SENSITIVE: 3,
    ActionType.DELETE: 4, ActionType.FINANCIAL: 4, ActionType.SELF_PERMISSION: 5,
}

# Patrons intention→type. Verbe d'ACTION (pas méta comme analyser/documenter/résumer).
_RULES = [
    (ActionType.SELF_PERMISSION,
     re.compile(r"(modif|chang|elev|augment|escalad|acquer|octroi)\w*.{0,25}(permission|droit|privileg)"
                r"|mes\s+(permission|droit|privileg)")),
    (ActionType.FINANCIAL,
     re.compile(r"ordre de virement|(effectu|fair|programm|initi|lanc)\w*.{0,12}virement"
                r"|virement de|\bpayer\b|paiement de|regler\b|transf\w+.{0,15}(fond|argent|euro|somme)")),
    (ActionType.EXTERNAL_SENSITIVE,
     re.compile(r"(envoy|transmet|exfiltr|publi|post|partag|upload|divulg)\w*.{0,30}"
                r"(dehors|externe|exterieur|hors|internet|tiers|public)")),
    (ActionType.DELETE,
     re.compile(r"/dev/null|supprim\w+|effac\w+|detrui\w+|\bpurg\w+|rm\s+-rf|\bwipe\b")),
]


class ReclassifierGate:
    def effective_type(self, action: Action) -> ActionType:
        text = _norm(f"{action.description} {action.target}")
        best = action.type
        for atype, rx in _RULES:
            if _RANK[atype] > _RANK[best] and rx.search(text):
                best = atype
        return best

    def reclassify(self, action: Action) -> Action:
        eff = self.effective_type(action)
        if eff is action.type:
            return action
        return dataclasses.replace(action, type=eff)
