"""FlagVerifier — ferme la fuite « mensonge sur les drapeaux » par la PREUVE, pas le lexique.

Modèle de menace (CODEX/03_GOUVERNANCE/02_Modele_de_menace.md) : la gouvernance v0 fait
confiance à ce que l'agent DÉCLARE (``has_backup``, ``validated``). Un agent qui ment
contourne GR-1/GR-7 (banc adverse : ment_backup, ment_validation).

Correctif : un drapeau ``True`` n'est CONSERVÉ que si une **preuve signée liée à CETTE
action précise** l'accompagne. Sinon le drapeau est forcé à ``False`` → le PolicyEngine
applique GR-1 (suppression sans backup → DENY) / GR-7 (finance non validée → validation).

- Réutilise la primitive HMAC prouvée de ``licensing/license.py`` (``sign_token``/``verify_token``).
- **Anti-rejeu** : la preuve est liée à ``sha256(type|target)`` ; une preuve d'une AUTRE action
  (ou d'un autre fichier) ne vérifie pas.
- Robuste à la paraphrase (contrairement à un filtre lexical) : la fermeture repose sur une
  vérité cryptographique, pas sur les mots de la description.

Limite honnête (v0) : le jeton atteste qu'un détenteur du secret (ex. le système de sauvegarde)
a certifié le backup ; le durcissement « vérifier sha256(fichier réel) » est la variante forte
(question de recherche 3, RESET.md).
"""

from __future__ import annotations

import dataclasses
import hashlib

from ..licensing.license import sign_token, verify_token
from .policy import Action


def _action_key(action: Action) -> str:
    """Identité d'une action pour lier une preuve (anti-rejeu)."""
    raw = f"{action.type.value}|{action.target}"
    return hashlib.sha256(raw.encode()).hexdigest()


class FlagVerifier:
    def __init__(self, secret: str) -> None:
        self._secret = secret

    # --- côté détenteur du secret : émettre des preuves légitimes ---
    def mint_backup_proof(self, action: Action) -> str:
        return sign_token(f"{_action_key(action)}|backup", self._secret)

    def mint_validation_proof(self, action: Action) -> str:
        return sign_token(f"{_action_key(action)}|validated", self._secret)

    # --- côté gouvernance : dégrader les drapeaux non prouvés ---
    def verify(self, action: Action) -> Action:
        """Retourne une action où has_backup/validated ne restent True que si prouvés."""
        proofs = {}
        if isinstance(action.metadata, dict):
            proofs = action.metadata.get("proofs", {}) or {}
        key = _action_key(action)

        has_backup = action.has_backup
        if has_backup and not verify_token(f"{key}|backup", proofs.get("backup", ""), self._secret):
            has_backup = False  # déclaré mais non prouvé → dégradé (fail-closed)

        validated = action.validated
        if validated and not verify_token(f"{key}|validated", proofs.get("validated", ""), self._secret):
            validated = False

        if has_backup == action.has_backup and validated == action.validated:
            return action  # rien à changer
        return dataclasses.replace(action, has_backup=has_backup, validated=validated)
