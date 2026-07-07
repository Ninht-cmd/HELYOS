"""Analyste de marché gouverné — analyse librement, ne trade JAMAIS seul.

Le contrat, brutalement honnête :
- ``analyze``      : lecture de prix publics + indicateurs classiques (SMA, RSI).
  C'est de l'OBSERVATION, pas de la prédiction, pas un conseil financier.
- ``propose_trade``: toute proposition d'ordre = Action FINANCIAL -> **GR-7 :
  validation humaine obligatoire, même en A5**. Et même validée, l'exécution
  retourne ``executed=False`` : AUCUN courtier n'est branché. HELYOS prépare,
  l'humain décide, et aujourd'hui l'humain exécute lui-même chez son courtier.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from ..connectors.market import MarketDataConnector
from ..governance.autonomy import AutonomyLevel
from ..governance.policy import Action, ActionType, PolicyVerdict
from ..governance.service import GovernanceService
from .base import Agent

# symboles compris dans le langage naturel -> paires Binance (prix en USDT)
SYMBOLS = {"btc": "BTCUSDT", "bitcoin": "BTCUSDT", "eth": "ETHUSDT",
           "ethereum": "ETHUSDT", "sol": "SOLUSDT", "solana": "SOLUSDT",
           "bnb": "BNBUSDT", "xrp": "XRPUSDT", "doge": "DOGEUSDT"}
DEFAULT_SYMBOLS = ("BTCUSDT", "ETHUSDT")


def sma(values: list[float], period: int) -> float | None:
    if len(values) < period:
        return None
    return sum(values[-period:]) / period


def rsi(values: list[float], period: int = 14) -> float | None:
    """RSI de Wilder simplifié (moyennes simples sur ``period`` variations)."""
    if len(values) < period + 1:
        return None
    deltas = [values[i] - values[i - 1] for i in range(len(values) - period, len(values))]
    gains = sum(d for d in deltas if d > 0) / period
    losses = sum(-d for d in deltas if d < 0) / period
    if losses == 0:
        return 100.0
    return round(100 - 100 / (1 + gains / losses), 1)


@dataclass(frozen=True)
class MarketBrief:
    symbol: str
    price_usdt: float
    change_24h_pct: float
    sma20: float | None
    sma50: float | None
    trend: str          # « haussière » / « baissière » / « indéterminée »
    rsi14: float | None
    note: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class MarketAnalystAgent(Agent):
    name = "market_analyst"
    description = ("Analyse le marché crypto (données publiques, lecture seule). "
                   "Toute proposition d'ordre exige la validation humaine (GR-7) ; "
                   "aucun courtier branché : ne peut pas exécuter.")
    required_level = AutonomyLevel.A1

    def __init__(self, market: MarketDataConnector | None = None) -> None:
        self.market = market or MarketDataConnector()

    def propose(self, context: dict[str, Any]) -> Action:
        return Action(type=ActionType.ANALYZE, actor=self.name,
                      description=f"Analyser le marché : {context.get('symbols', DEFAULT_SYMBOLS)}")

    # --- analyse (A1, lecture seule) ---
    def analyze(self, governance: GovernanceService,
                symbols: tuple[str, ...] = DEFAULT_SYMBOLS,
                granted: AutonomyLevel = AutonomyLevel.A1,
                ) -> tuple[PolicyVerdict, list[MarketBrief]]:
        verdict = governance.submit(self.propose({"symbols": symbols}), granted)
        if not verdict.allowed:
            return verdict, []
        briefs = []
        for s in symbols:
            t = self.market.ticker(s)
            closes = self.market.daily_closes(s, 60)
            s20, s50, r = sma(closes, 20), sma(closes, 50), rsi(closes)
            trend = ("indéterminée" if s20 is None or s50 is None
                     else "haussière" if s20 > s50 else "baissière")
            note = ("suracheté (RSI>70)" if r is not None and r > 70
                    else "survendu (RSI<30)" if r is not None and r < 30 else "zone neutre")
            briefs.append(MarketBrief(
                symbol=s, price_usdt=float(t.get("lastPrice", 0)),
                change_24h_pct=round(float(t.get("priceChangePercent", 0)), 2),
                sma20=None if s20 is None else round(s20, 2),
                sma50=None if s50 is None else round(s50, 2),
                trend=trend, rsi14=r, note=note))
        return verdict, briefs

    @staticmethod
    def summary_text(briefs: list[MarketBrief]) -> str:
        if not briefs:
            return "Aucune donnée de marché disponible."
        lines = ["Analyse du marché (données publiques Binance, prix en USDT) :"]
        for b in briefs:
            ind = (f"SMA20 {b.sma20} / SMA50 {b.sma50} → tendance {b.trend}"
                   if b.sma20 is not None and b.sma50 is not None else "historique insuffisant")
            lines.append(f"  • {b.symbol} : {b.price_usdt:,.0f} $ ({b.change_24h_pct:+.2f} % / 24 h) — "
                         f"{ind} · RSI14 {b.rsi14} ({b.note})")
        lines.append("Observation technique, pas un conseil financier ni une prédiction.")
        return "\n".join(lines)

    # --- proposition d'ordre (GR-7 : jamais autonome ; exécution inexistante) ---
    def propose_trade(self, governance: GovernanceService, *, symbol: str, side: str,
                      amount_eur: float, granted: AutonomyLevel = AutonomyLevel.A2,
                      validated: bool = False,
                      ) -> tuple[PolicyVerdict, dict[str, Any]]:
        action = Action(
            type=ActionType.FINANCIAL, actor=self.name,
            description=f"Proposition d'ordre : {side} {symbol} pour {amount_eur:.2f} €",
            validated=validated)
        verdict = governance.submit(action, granted)
        return verdict, {
            "symbol": symbol, "side": side, "amount_eur": amount_eur,
            "executed": False,   # par conception : aucun courtier n'est branché
            "reason": ("validation requise (GR-7)" if not verdict.allowed
                       else "aucun courtier branché — HELYOS prépare, tu exécutes chez ton courtier"),
        }
