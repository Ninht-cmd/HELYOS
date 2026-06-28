"""Bus d'événements en mémoire — la colonne vertébrale du Kernel.

Décision : ADR-0004. Les composants publient/écoutent des événements plutôt
que de s'appeler directement (découplage, observabilité, modularité).

Implémentation par défaut : en mémoire, synchrone, zéro dépendance (Local First).
L'interface est conçue pour qu'une implémentation Redis puisse la remplacer sans
changer les composants appelants.
"""

from __future__ import annotations

import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

# Un handler reçoit l'événement et ne retourne rien.
Handler = Callable[["Event"], None]


@dataclass(frozen=True)
class Event:
    """Un événement immuable circulant sur le bus.

    name suit une convention pointée : ``domaine.action`` (ex. ``presence.detected``,
    ``intent.received``, ``governance.decided``, ``action.executed``).
    """

    name: str
    payload: dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    ts: float = field(default_factory=time.time)


def _matches(pattern: str, name: str) -> bool:
    """Correspondance simple : exacte, ``*`` (tout), ou préfixe ``domaine.*``."""
    if pattern == "*":
        return True
    if pattern.endswith(".*"):
        return name == pattern[:-2] or name.startswith(pattern[:-1])
    return pattern == name


class EventBus:
    """Bus pub/sub synchrone en mémoire.

    - ``subscribe(pattern, handler)`` : s'abonner (pattern exact ou ``domaine.*``).
    - ``publish(event)`` : diffuser à tous les abonnés correspondants.
    - ``history`` : trace des événements publiés (observabilité — ADN 6).
    """

    def __init__(self, keep_history: int = 1000) -> None:
        self._subscriptions: list[tuple[str, Handler]] = []
        self._history: list[Event] = []
        self._keep_history = keep_history

    def subscribe(self, pattern: str, handler: Handler) -> Callable[[], None]:
        """Abonne un handler. Retourne une fonction de désabonnement."""
        entry = (pattern, handler)
        self._subscriptions.append(entry)

        def unsubscribe() -> None:
            try:
                self._subscriptions.remove(entry)
            except ValueError:
                pass

        return unsubscribe

    def publish(self, event: Event) -> int:
        """Publie un événement. Retourne le nombre de handlers notifiés.

        Un handler qui lève une exception n'interrompt pas la diffusion aux
        autres (isolation des abonnés).
        """
        self._record(event)
        notified = 0
        for pattern, handler in list(self._subscriptions):
            if _matches(pattern, event.name):
                try:
                    handler(event)
                    notified += 1
                except Exception:  # pragma: no cover - isolation défensive
                    # En production : journaliser via l'observabilité.
                    continue
        return notified

    def emit(self, name: str, **payload: Any) -> Event:
        """Raccourci : construit et publie un événement."""
        event = Event(name=name, payload=dict(payload))
        self.publish(event)
        return event

    def _record(self, event: Event) -> None:
        self._history.append(event)
        if len(self._history) > self._keep_history:
            self._history = self._history[-self._keep_history :]

    @property
    def history(self) -> list[Event]:
        return list(self._history)

    def clear_history(self) -> None:
        self._history.clear()
