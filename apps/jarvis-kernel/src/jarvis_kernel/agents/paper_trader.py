"""Trading en SIMULATION — argent fictif, prix réels, vérité affichée partout.

Ce module répond à « je veux qu'HELYOS investisse » de la seule façon honnête
possible aujourd'hui : un portefeuille VIRTUEL (1 000 € fictifs) qui exécute la
stratégie SMA/RSI sur les prix réels du marché et mesure son P&L sans complaisance.

Ce que ce module N'EST PAS, par construction :
- Il ne touche JAMAIS un euro réel : aucun courtier, aucune clé, aucun ordre.
- Il ne « prouve » rien tant que le P&L simulé n'a pas survécu longtemps
  (un backtest gagnant est facile ; ADR-0010 : PBO/Deflated Sharpe avant tout réel).
- Le passage au réel, si un jour : RFC dédiée + courtier + budgets + coupe-circuit
  + GR-7 (chaque ordre réel validé par le fondateur, à vie).
"""

from __future__ import annotations

import time
from typing import Any

from ..connectors.market import MarketDataConnector
from ..governance.autonomy import AutonomyLevel
from ..governance.policy import Action, ActionType, PolicyVerdict
from ..governance.service import GovernanceService
from ..memory.store import MemoryStore
from .base import Agent
from .market_analyst import rsi, sma

START_CASH = 1000.0          # capital de départ — FICTIF
_NS = "paper_trading"
LABEL = "SIMULATION — argent fictif, aucun ordre réel n'existe"


class PaperTrader(Agent):
    name = "paper_trader"
    description = ("Trading en simulation : capital FICTIF, prix réels, P&L honnête. "
                   "Banc d'essai avant tout euro réel (GR-7 : jamais d'argent autonome).")
    required_level = AutonomyLevel.A1

    def __init__(self, market: MarketDataConnector | None = None) -> None:
        self.market = market or MarketDataConnector()

    def propose(self, context: dict[str, Any]) -> Action:
        return Action(type=ActionType.ANALYZE, actor=self.name,
                      description="Simulation trading (argent FICTIF) : évaluer les signaux")

    def _wallet(self, memory: MemoryStore) -> dict:
        return memory.recall("wallet", namespace=_NS) or {
            "start_eur": START_CASH, "cash_eur": START_CASH,
            "positions": {}, "trades": [], "equity_eur": START_CASH, "pnl_pct": 0.0,
        }

    def step(self, governance: GovernanceService, memory: MemoryStore,
             symbols: tuple[str, ...] = ("BTCUSDT", "ETHUSDT"),
             granted: AutonomyLevel = AutonomyLevel.A1,
             ) -> tuple[PolicyVerdict, dict | None]:
        """Un pas de stratégie : signaux -> ordres VIRTUELS -> P&L. Gouverné (A1)."""
        verdict = governance.submit(self.propose({}), granted)
        if not verdict.allowed:
            return verdict, None

        w = self._wallet(memory)
        prices: dict[str, float] = {}
        executed = 0
        for sym in symbols:
            closes = self.market.daily_closes(sym, 60)
            price = closes[-1]
            prices[sym] = price
            s20, s50, r = sma(closes, 20), sma(closes, 50), rsi(closes)
            if s20 is None or s50 is None:
                continue
            pos = float(w["positions"].get(sym, 0.0))
            # stratégie assumée simple : croisement SMA + garde RSI. Pas une promesse.
            if s20 > s50 and (r or 50) < 70 and pos == 0 and w["cash_eur"] > 50:
                budget = round(w["cash_eur"] * 0.10, 2)      # 10 % du cash par position
                qty = budget / price
                w["cash_eur"] = round(w["cash_eur"] - budget, 2)
                w["positions"][sym] = qty
                w["trades"].append({"side": "achat", "symbol": sym, "qty": qty,
                                    "price": price, "eur": budget, "ts": time.time()})
                executed += 1
            elif s20 < s50 and pos > 0:
                eur = round(pos * price, 2)
                w["cash_eur"] = round(w["cash_eur"] + eur, 2)
                w["positions"].pop(sym, None)
                w["trades"].append({"side": "vente", "symbol": sym, "qty": pos,
                                    "price": price, "eur": eur, "ts": time.time()})
                executed += 1

        held = sum(float(q) * prices.get(s, 0.0) for s, q in w["positions"].items())
        w["equity_eur"] = round(w["cash_eur"] + held, 2)
        w["pnl_pct"] = round((w["equity_eur"] / w["start_eur"] - 1) * 100, 2)
        w["trades"] = w["trades"][-50:]
        w["last_step_ts"] = time.time()
        memory.remember("wallet", w, namespace=_NS)
        return verdict, {**self.summary(memory), "executed": executed}

    def summary(self, memory: MemoryStore) -> dict:
        """État du portefeuille virtuel — étiqueté simulation, toujours."""
        w = self._wallet(memory)
        return {
            "label": LABEL,
            "start_eur": w["start_eur"], "cash_eur": w["cash_eur"],
            "equity_eur": w.get("equity_eur", w["cash_eur"]),
            "pnl_pct": w.get("pnl_pct", 0.0),
            "positions": w["positions"], "trades": w["trades"][-5:],
            "trades_count": len(w["trades"]),
        }
