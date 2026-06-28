"""Observabilité — tout est observable (ADN 6).

Logs structurés en stdlib par défaut ; hooks prêts pour OpenTelemetry / Langfuse
(CODEX/07_TECH). Aucune dépendance requise pour le cœur.
"""

from .telemetry import configure_logging, get_logger
from .tracing import is_enabled, setup_tracing, span

__all__ = ["get_logger", "configure_logging", "setup_tracing", "span", "is_enabled"]
