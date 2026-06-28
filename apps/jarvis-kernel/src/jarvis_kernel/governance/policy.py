"""Moteur de politique — décide ALLOW / REQUIRE_VALIDATION / DENY.

Source de vérité :
- CODEX/03_GOUVERNANCE/00_Autonomie_A0_A5.md (niveaux requis par action)
- CODEX/03_GOUVERNANCE/01_Regles_Or.md (interdits absolus)

Ce module est le miroir *exécutable* du Codex. Les règles d'or sont appliquées
ici et couvertes par tests/test_governance.py. Une règle écrite mais non testée
n'est qu'un vœu (cf. ADR-0003).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from .autonomy import AutonomyLevel


class ActionType(Enum):
    """Types d'actions reconnus par le moteur."""

    READ = "read"  # lire/observer
    ANALYZE = "analyze"  # résumer, analyser, proposer un plan
    WRITE_LOCAL = "write_local"  # écrire/modifier un fichier local
    RENAME_WORKDIR = "rename_workdir"  # renommer dans un dossier de travail (réversible)
    DELETE = "delete"  # supprimer des données
    EXTERNAL_SENSITIVE = "external_sensitive"  # e-mail, publication, appel tiers sensible
    FINANCIAL = "financial"  # transaction financière
    SELF_PERMISSION = "self_permission"  # modifier ses propres permissions / niveau


class Decision(Enum):
    ALLOW = "allow"
    REQUIRE_VALIDATION = "require_validation"
    DENY = "deny"


# Niveau d'autonomie minimal requis par type d'action (miroir du Codex).
REQUIRED_LEVEL: dict[ActionType, AutonomyLevel] = {
    ActionType.READ: AutonomyLevel.A0,
    ActionType.ANALYZE: AutonomyLevel.A1,
    ActionType.WRITE_LOCAL: AutonomyLevel.A2,
    ActionType.RENAME_WORKDIR: AutonomyLevel.A3,
    ActionType.DELETE: AutonomyLevel.A2,
    ActionType.EXTERNAL_SENSITIVE: AutonomyLevel.A2,
    ActionType.FINANCIAL: AutonomyLevel.A2,
    ActionType.SELF_PERMISSION: AutonomyLevel.A5,  # plancher haut ; de toute façon interdit
}


@dataclass(frozen=True)
class Action:
    """Une action soumise à la gouvernance.

    Drapeaux contextuels qui activent les règles d'or :
    - ``has_backup`` : une sauvegarde vérifiable existe (requis pour DELETE — GR-1).
    - ``sensitive``  : action externe sensible (GR-2).
    - ``reversible`` : action réversible (catégorisation faible risque).
    - ``validated``  : le Conservateur a explicitement approuvé CETTE action.
    """

    type: ActionType
    description: str = ""
    target: str = ""
    actor: str = "unknown"
    has_backup: bool = False
    sensitive: bool = False
    reversible: bool = False
    validated: bool = False
    metadata: dict = field(default_factory=dict)


@dataclass(frozen=True)
class PolicyVerdict:
    """Résultat d'une évaluation."""

    decision: Decision
    reason: str
    required_level: AutonomyLevel
    granted_level: AutonomyLevel
    rule: str | None = None  # identifiant de règle d'or si déclenchée (ex. "GR-1")

    @property
    def allowed(self) -> bool:
        return self.decision is Decision.ALLOW


class PolicyEngine:
    """Évalue une action contre un niveau accordé. Pur, sans effet de bord."""

    def required_level(self, action: Action) -> AutonomyLevel:
        return REQUIRED_LEVEL.get(action.type, AutonomyLevel.A2)

    def evaluate(self, action: Action, granted: AutonomyLevel) -> PolicyVerdict:
        required = self.required_level(action)

        def verdict(decision: Decision, reason: str, rule: str | None = None) -> PolicyVerdict:
            return PolicyVerdict(
                decision=decision,
                reason=reason,
                required_level=required,
                granted_level=granted,
                rule=rule,
            )

        # --- 1. Règles d'or à DENY absolu (non rattrapables par validation) ---

        # GR-3 : pas d'auto-escalade des permissions.
        if action.type is ActionType.SELF_PERMISSION:
            return verdict(
                Decision.DENY,
                "Auto-escalade interdite : un agent ne modifie pas ses propres permissions.",
                rule="GR-3",
            )

        # GR-1 : pas de suppression sans sauvegarde.
        if action.type is ActionType.DELETE and not action.has_backup:
            return verdict(
                Decision.DENY,
                "Suppression refusée : aucune sauvegarde vérifiable (GR-1). "
                "Effectuer une sauvegarde avant de réessayer.",
                rule="GR-1",
            )

        # --- 2. Règles d'or à validation forcée (rattrapables par accord humain) ---

        # GR-7 : aucune transaction financière n'est jamais autonome.
        if action.type is ActionType.FINANCIAL and not action.validated:
            return verdict(
                Decision.REQUIRE_VALIDATION,
                "Action financière : validation humaine obligatoire, jamais autonome (GR-7).",
                rule="GR-7",
            )

        # GR-2 : action externe sensible sans validation -> validation requise.
        is_external = action.type is ActionType.EXTERNAL_SENSITIVE or action.sensitive
        if is_external and not action.validated:
            return verdict(
                Decision.REQUIRE_VALIDATION,
                "Action externe sensible : validation humaine requise (GR-2).",
                rule="GR-2",
            )

        # --- 3. Vérification du niveau d'autonomie ---
        if granted >= required:
            return verdict(
                Decision.ALLOW,
                f"Niveau accordé {granted.name} ≥ requis {required.name}.",
            )

        # Niveau insuffisant mais rattrapable par validation humaine.
        return verdict(
            Decision.REQUIRE_VALIDATION,
            f"Niveau accordé {granted.name} < requis {required.name} : "
            "validation humaine requise pour exécuter.",
        )
