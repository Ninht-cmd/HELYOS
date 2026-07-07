"""Connecteur données de marché — API publique Binance, LECTURE SEULE.

Pas de clé, pas de compte, et surtout : AUCUNE capacité d'ordre. Ce connecteur
ne sait que lire des prix publics. L'exécution d'ordres n'existe pas par
conception (GR-7 : aucune transaction financière autonome, jamais).

Distinct de TradingView (interdit, ADR-0010) : ici on lit une API publique
officielle et documentée, ce qui est licite et stable.
"""

from __future__ import annotations

from .base import Connector, ConnectorStatus, Transport, default_transport

_BASE = "https://api.binance.com/api/v3"


class MarketDataConnector(Connector):
    name = "market"
    kind = "finance"

    def __init__(self, transport: Transport | None = None) -> None:
        self.transport = transport or default_transport

    def status(self) -> ConnectorStatus:
        return ConnectorStatus(
            self.name, self.kind, "connected",
            detail="Binance API publique · lecture seule · aucune clé, aucun ordre possible")

    def ticker(self, symbol: str) -> dict:
        """Prix et variation 24 h. ``symbol`` ex. BTCUSDT (prix exprimés en USDT)."""
        return self.transport(f"{_BASE}/ticker/24hr?symbol={symbol}", {})

    def daily_closes(self, symbol: str, days: int = 60) -> list[float]:
        """Clôtures quotidiennes (max 60 j) pour les indicateurs."""
        days = max(2, min(days, 200))
        klines = self.transport(f"{_BASE}/klines?symbol={symbol}&interval=1d&limit={days}", {})
        return [float(k[4]) for k in klines]     # k[4] = close
