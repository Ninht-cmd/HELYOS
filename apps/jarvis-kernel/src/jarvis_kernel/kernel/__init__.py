"""Cœur du Kernel : le bus d'événements (colonne vertébrale — ADR-0004)."""

from .event_bus import Event, EventBus

__all__ = ["Event", "EventBus"]
