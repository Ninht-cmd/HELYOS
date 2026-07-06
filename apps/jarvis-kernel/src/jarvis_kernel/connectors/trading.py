"""TradingView — connecteur INTERDIT, et il le dit.

Décision ADR-0010 (vérifiée) : TradingView n'a pas d'API publique officielle et
ses conditions d'utilisation (§3) interdisent le trading automatisé — risque de
bannissement et risque juridique. Par ailleurs GR-7 interdit toute transaction
financière autonome, à vie.

Ce module N'APPELLE JAMAIS TradingView. Il existe pour que l'interface affiche
le refus et sa raison, au lieu de laisser croire qu'un branchement est possible.
Alternative gouvernée [CHANTIER] : backtest NautilusTrader (jamais d'ordres réels).
"""

from __future__ import annotations

from .base import Connector, ConnectorStatus


class TradingViewConnector(Connector):
    name = "tradingview"
    kind = "finance"

    def status(self) -> ConnectorStatus:
        return ConnectorStatus(
            self.name, self.kind, "forbidden",
            detail="ADR-0010 : pas d'API officielle, CGU §3 = trading automatisé interdit "
                   "(ban + juridique) ; GR-7 : aucune transaction autonome, jamais. "
                   "Alternative [CHANTIER] : backtest NautilusTrader, sans ordres réels.",
        )
