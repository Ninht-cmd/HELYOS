"""Logs structurés (JSON) en bibliothèque standard.

Conçu pour être remplacé/complété par OpenTelemetry et Langfuse sans changer les
appels ``get_logger(__name__).info(...)`` côté composants.
"""

from __future__ import annotations

import json
import logging
import sys
import time
from typing import Any


class _JsonFormatter(logging.Formatter):
    """Formate chaque enregistrement en une ligne JSON (prêt pour Loki/OTel)."""

    def format(self, record: logging.LogRecord) -> str:
        base: dict[str, Any] = {
            "ts": round(record.created, 3),
            "iso": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(record.created)),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        # Champs structurés passés via extra={"context": {...}}
        context = getattr(record, "context", None)
        if isinstance(context, dict):
            base["context"] = context
        if record.exc_info:
            base["exc"] = self.formatException(record.exc_info)
        return json.dumps(base, ensure_ascii=False)


_configured = False


def configure_logging(level: int = logging.INFO) -> None:
    """Configure une fois le logging structuré sur stdout."""
    global _configured
    if _configured:
        return
    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setFormatter(_JsonFormatter())
    root = logging.getLogger("helyos")
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)
    root.propagate = False
    _configured = True


def get_logger(name: str) -> logging.Logger:
    """Retourne un logger sous l'espace de noms ``helyos.*``."""
    configure_logging()
    short = name.split(".")[-1]
    return logging.getLogger(f"helyos.{short}")
