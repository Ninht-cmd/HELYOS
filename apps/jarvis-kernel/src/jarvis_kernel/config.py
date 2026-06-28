"""Configuration du Kernel.

Lecture depuis l'environnement, sans dépendance externe (stdlib uniquement),
pour préserver le démarrage local-first. Voir CODEX/07_TECH.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from .governance.autonomy import AutonomyLevel


def _env(name: str, default: str) -> str:
    value = os.environ.get(name)
    return value if value is not None and value != "" else default


@dataclass(frozen=True)
class Settings:
    """Paramètres du Kernel, immuables une fois chargés."""

    app_name: str = "HELYOS Jarvis Kernel"
    version: str = "0.2.0"
    host: str = "127.0.0.1"
    port: int = 8080
    # Niveau d'autonomie accordé par défaut à une session sans mandat explicite.
    # ADN / Gouvernance : le défaut est BAS (A1 = préparer, ne pas agir).
    default_autonomy: AutonomyLevel = AutonomyLevel.A1

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            app_name=_env("HELYOS_APP_NAME", "HELYOS Jarvis Kernel"),
            version=_env("HELYOS_VERSION", "0.2.0"),
            host=_env("HELYOS_HOST", "127.0.0.1"),
            port=int(_env("HELYOS_PORT", "8080")),
            default_autonomy=AutonomyLevel.from_name(
                _env("HELYOS_DEFAULT_AUTONOMY", "A1")
            ),
        )


# Instance partagée, chargée à l'import.
settings = Settings.from_env()
