"""Connecteurs vers le monde réel — TOUS derrière la gouvernance.

Doctrine (ADR-0010, RFC-0009) :
- Lecture (sync de métriques) = ANALYZE (A1), tracée sur le bus.
- Écriture vers l'extérieur (e-mail, publication) = EXTERNAL_SENSIBLE -> GR-2,
  validation humaine obligatoire, même en A5.
- Un connecteur non configuré le DIT (« à connecter » + ce qu'il faut fournir).
- Un connecteur interdit le DIT aussi (TradingView : ADR-0010).
Stdlib uniquement (urllib, smtplib) — Local First, zéro dépendance.
"""

from .base import Connector, ConnectorStatus, EnvConnector
from .registry import build_connectors

__all__ = ["Connector", "ConnectorStatus", "EnvConnector", "build_connectors"]
