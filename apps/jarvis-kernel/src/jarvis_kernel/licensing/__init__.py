"""Licence & entitlements — le mécanisme de monétisation, format ouvert.

Le cœur expose le format/algorithme ; le secret de signature reste hors du dépôt
public (côté Pro/cloud). Voir CODEX/09_LEGAL et CODEX/05_ECONOMIE.
"""

from .license import (
    COMMUNITY,
    Entitlements,
    LicenseError,
    require,
    sign_license,
    sign_token,
    verify_license,
    verify_token,
)

__all__ = [
    "Entitlements",
    "LicenseError",
    "COMMUNITY",
    "sign_license",
    "verify_license",
    "require",
    "sign_token",
    "verify_token",
]
