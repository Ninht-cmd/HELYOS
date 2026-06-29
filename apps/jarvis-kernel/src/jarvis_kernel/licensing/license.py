"""Moteur de licence / entitlements — format ouvert, vérification transparente.

Le CŒUR (open) publie le FORMAT et l'ALGORITHME de vérification (transparence,
principe de Kerckhoffs : la sécurité ne repose pas sur le secret de l'algo). Le
SECRET de signature reste côté Pro / cloud (jamais dans le dépôt public).

C'est le mécanisme « téléchargement → tu es payé » : une fonctionnalité payante
exige une licence signée valide, sinon elle refuse de s'exécuter (fail-closed).

Modèle v0 : HMAC-SHA256 (symétrique, stdlib, zéro dépendance).
Évolution (RFC) : signatures asymétriques Ed25519 (vérif par clé publique) et/ou
activation en ligne via helyos-cloud. Voir CODEX/09_LEGAL.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from dataclasses import dataclass


class LicenseError(Exception):
    """Levée quand une licence est absente, invalide, expirée, ou insuffisante."""


@dataclass(frozen=True)
class Entitlements:
    """Les droits accordés par une licence."""

    licensee: str
    features: frozenset[str]
    expires: float | None = None  # epoch UTC, ou None = perpétuel

    @property
    def expired(self) -> bool:
        return self.expires is not None and time.time() > self.expires

    def has(self, feature: str) -> bool:
        if self.expired:
            return False
        return "*" in self.features or feature in self.features


#: Droits par défaut : communauté (cœur AGPL) — aucune fonctionnalité Pro.
COMMUNITY = Entitlements(licensee="community", features=frozenset())


def _b64e(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _b64d(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def sign_license(payload: dict, secret: str) -> str:
    """Crée une clé de licence signée (à exécuter côté détenteur du secret)."""
    body = _b64e(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode())
    sig = _b64e(hmac.new(secret.encode(), body.encode(), hashlib.sha256).digest())
    return f"{body}.{sig}"


def verify_license(key: str, secret: str) -> Entitlements:
    """Vérifie une clé et retourne les droits. Lève LicenseError si invalide/expirée."""
    try:
        body, sig = key.strip().split(".")
        expected = _b64e(hmac.new(secret.encode(), body.encode(), hashlib.sha256).digest())
    except Exception as exc:
        raise LicenseError(f"Clé de licence illisible : {exc}") from exc
    if not hmac.compare_digest(sig, expected):
        raise LicenseError("Signature de licence invalide.")
    payload = json.loads(_b64d(body))
    ent = Entitlements(
        licensee=str(payload.get("licensee", "?")),
        features=frozenset(payload.get("features", [])),
        expires=payload.get("expires"),
    )
    if ent.expired:
        raise LicenseError("Licence expirée.")
    return ent


def require(entitlements: Entitlements, feature: str) -> None:
    """Garde fail-closed : lève LicenseError si la fonctionnalité n'est pas couverte."""
    if not entitlements.has(feature):
        raise LicenseError(
            f"Fonctionnalité « {feature} » non incluse dans votre licence "
            f"(titulaire : {entitlements.licensee}). Une licence HELYOS Pro est requise."
        )
