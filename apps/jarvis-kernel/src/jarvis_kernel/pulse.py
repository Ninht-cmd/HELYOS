"""Le Pouls — ce qui fait d'HELYOS un Jarvis et non un chatbot.

Un chatbot attend qu'on lui parle. Un Jarvis observe en continu et parle en
premier quand quelque chose mérite ton attention. Le Pouls est cette boucle :
il surveille les validations en attente, les tâches humaines bloquantes, le
marché et les connecteurs, puis compose le briefing du Prompt Fondateur —
« chaque matin, uniquement les décisions, les anomalies, les priorités.
Le silence signifie que tout fonctionne. »

Contrat d'honnêteté et de sécurité :
- Le Pouls OBSERVE, il n'agit JAMAIS. Aucune action monde, aucune écriture
  externe. Il lit l'état interne (audit, portefeuille) et des prix publics.
- Il n'inonde pas l'audit : observer l'état interne n'est pas une action
  gouvernable ; seules ses ALERTES laissent une trace (bus + mémoire).
- Il ne crashe jamais le kernel : chaque veilleur est isolé ; un échec réseau
  devient une absence d'information, pas une panne.
"""

from __future__ import annotations

import threading
import time
from dataclasses import asdict, dataclass, field

from .context import KernelContext
from .observability.telemetry import get_logger

logger = get_logger(__name__)

# seuil d'alerte marché : |variation 24 h| au-delà = signalé dans le briefing
MARKET_MOVE_PCT = 5.0
# throttle des lectures marché (API publique : on reste poli) — secondes
MARKET_EVERY_S = 600.0


@dataclass
class PulseItem:
    """Une ligne du briefing : quoi, pourquoi, quelle urgence."""

    kind: str          # validation | task | market | connector
    text: str
    urgent: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Pulse:
    """Boucle d'observation. ``tick()`` est pur et testable ; la boucle de fond
    ne fait que l'appeler à intervalle régulier."""

    ctx: KernelContext
    market_move_pct: float = MARKET_MOVE_PCT
    clock: object = time.monotonic          # injectable pour les tests
    _last_market: float = field(default=-1e12, repr=False)
    _last_items: list = field(default_factory=list, repr=False)
    _last_failures: list = field(default_factory=list, repr=False)
    _stop: threading.Event = field(default_factory=threading.Event, repr=False)
    _thread: threading.Thread | None = field(default=None, repr=False)
    # tick() est appelé par le thread de fond ET par les requêtes HTTP/MCP :
    # sans verrou, alertes dupliquées et état déchiré.
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    @property
    def last_items(self) -> list[PulseItem]:
        """Dernières observations (pour l'API) — jamais None."""
        return list(self._last_items)

    # ---- veilleurs (chacun isolé : un échec = pas d'info, pas de panne) ----
    def _watch_validations(self) -> list[PulseItem]:
        # L'audit est append-only : une demande est considérée traitée quand une
        # décision ULTÉRIEURE (allow après validation, ou deny) porte la même
        # description. Heuristique — mais sans elle le compteur ne redescendrait jamais.
        entries = self.ctx.governance.audit.tail(300)
        pending: dict[str, object] = {}
        for e in entries:
            if e.decision == "require_validation":
                pending[e.action_description] = e
            elif e.decision in ("allow", "deny"):
                pending.pop(e.action_description, None)
        if not pending:
            return []
        last = next(reversed(pending.values()))
        return [PulseItem("validation", f"{len(pending)} action(s) attendent ta validation — "
                          f"dernière : « {last.action_description[:80]} » ({last.rule or 'gouvernance'}).",
                          urgent=True)]

    def _watch_tasks(self) -> list[PulseItem]:
        items: list[PulseItem] = []
        for b in self.ctx.portfolio.list():
            humans = [t["task"] for t in b.tasks
                      if not t.get("done") and str(t.get("owner", "")).lower() == "humain"]
            if humans:
                items.append(PulseItem(
                    "task", f"{b.name} : {len(humans)} tâche(s) t'attendent — "
                            f"prochaine : {humans[0].replace('[HUMAIN] ', '')}"))
        return items[:3]                     # briefing court, pas une todo-list complète

    def _watch_market(self) -> list[PulseItem]:
        now = self.clock()
        if now - self._last_market < MARKET_EVERY_S:
            return [i for i in self._last_items if i.kind == "market"]
        self._last_market = now
        market = next((c for c in (self.ctx.connectors or []) if c.name == "market"), None)
        if market is None:
            return []
        try:
            items = []
            for sym in ("BTCUSDT", "ETHUSDT"):
                t = market.ticker(sym)
                pct = float(t.get("priceChangePercent", 0) or 0)
                price = float(t.get("lastPrice", 0) or 0)
                if abs(pct) >= self.market_move_pct:
                    items.append(PulseItem(
                        "market", f"{sym} bouge fort : {pct:+.1f} % / 24 h ({price:,.0f} $). "
                                  "Observation, pas un conseil.", urgent=False))
            return items
        except Exception:                    # réseau coupé : silence, pas d'invention
            return []

    def _watch_prospection(self) -> list[PulseItem]:
        from .business.prospection import ProspectionPipeline

        due = ProspectionPipeline(self.ctx.memory).due_followups()
        if not due:
            return []
        names = ", ".join(p.name for p, _ in due[:4])
        return [PulseItem("prospection",
                          f"{len(due)} relance(s) de prospection à envoyer (J+3/J+7) : {names}.",
                          urgent=True)]

    def _watch_paper(self) -> list[PulseItem]:
        w = self.ctx.memory.recall("wallet", namespace="paper_trading")
        if not w:
            return []                        # pas de simulation démarrée : silence
        return [PulseItem("paper",
                          f"Simulation trading (FICTIF) : {w.get('equity_eur', 0):.2f} € "
                          f"({w.get('pnl_pct', 0):+.2f} %), {len(w.get('trades', []))} ordre(s) virtuels.")]

    def _watch_connectors(self) -> list[PulseItem]:
        try:
            waiting = [c.name for c in (self.ctx.connectors or [])
                       if c.status().status == "not_configured" and c.name in ("shopify", "smtp")]
        except Exception:
            return []
        if not waiting:
            return []
        return [PulseItem("connector",
                          f"Connecteurs utiles au Plan Cash toujours débranchés : {', '.join(waiting)}.")]

    # ---- battement ----
    def tick(self) -> list[PulseItem]:
        """Un battement : collecte les observations et publie ce qui a changé."""
        with self._lock:                     # sérialise fond + HTTP + MCP
            items: list[PulseItem] = []
            failures: list[str] = []
            for watcher in (self._watch_validations, self._watch_tasks,
                            self._watch_prospection, self._watch_market,
                            self._watch_paper, self._watch_connectors):
                try:
                    items.extend(watcher())
                except Exception:            # aucun veilleur ne tue le pouls…
                    failures.append(watcher.__name__.replace("_watch_", ""))
                    logger.warning("veilleur en échec",
                                   extra={"context": {"w": watcher.__name__}})
            # n'émettre sur le bus QUE les nouveautés (sinon le flux devient du bruit)
            old = {i.text for i in self._last_items}
            for it in items:
                if it.text not in old:
                    self.ctx.bus.emit("pulse.alert" if it.urgent else "pulse.note",
                                      kind=it.kind, text=it.text)
            self._last_items = items
            self._last_failures = failures   # …mais son échec ne devient pas du silence
            self.ctx.memory.remember("last_briefing", [i.to_dict() for i in items],
                                     namespace="pulse")
            return items

    def report(self) -> tuple[str, list[PulseItem]]:
        """UN battement -> (texte, items) cohérents entre eux (pas de relecture TOCTOU)."""
        items = self.tick()
        failures = list(self._last_failures)
        if not items:
            if failures:
                # honnêteté : un veilleur aveugle n'est pas un veilleur serein
                return (f"Aucune alerte, mais je n'ai pas pu tout observer "
                        f"(veilleur(s) en échec : {', '.join(failures)}) — information partielle.",
                        items)
            return ("Rien à signaler : pas de validation en attente, pas d'anomalie. "
                    "Le silence signifie que tout fonctionne.", items)
        lines = ["Briefing HELYOS :"]
        lines += [f"  • {'⚠ ' if i.urgent else ''}{i.text}" for i in items]
        if failures:
            lines.append(f"  • ⚠ Veilleur(s) en échec : {', '.join(failures)} — information partielle.")
        lines.append("Le reste fonctionne — je me tais dessus.")
        return "\n".join(lines), items

    def briefing(self) -> str:
        """Le briefing du Prompt Fondateur — court, décisionnel, honnête."""
        return self.report()[0]

    # ---- boucle de fond (facultative ; tick() reste utilisable sans elle) ----
    def start(self, interval_s: float = 60.0) -> None:
        if self._thread is not None or interval_s <= 0:
            return
        if self._stop.is_set():              # réarme après un stop() : sinon Pouls mort-né
            self._stop = threading.Event()

        def _loop() -> None:
            while not self._stop.wait(interval_s):
                try:
                    self.tick()
                except Exception:            # ceinture ET bretelles
                    logger.warning("battement en échec")

        self._thread = threading.Thread(target=_loop, name="helyos-pulse", daemon=True)
        self._thread.start()
        logger.info("Pouls démarré", extra={"context": {"interval_s": interval_s}})

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2)
            self._thread = None
