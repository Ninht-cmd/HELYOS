"""Journal d'audit — trace immuable des décisions de gouvernance.

Source de vérité : ADN 16 (« aucune décision importante ne reste dans une
conversation ») et GR-5 (traçabilité totale).

Implémentation v0 : en mémoire, append-only. Cible Alpha : Postgres (RFC-0001,
question ouverte). L'interface reste stable.
"""

from __future__ import annotations

import time
import uuid
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class AuditEntry:
    """Une entrée d'audit immuable : qui, quoi, décision, pourquoi, quand."""

    actor: str
    action_type: str
    action_description: str
    decision: str
    reason: str
    rule: str | None
    required_level: str
    granted_level: str
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    ts: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "ts": self.ts,
            "actor": self.actor,
            "action_type": self.action_type,
            "action_description": self.action_description,
            "decision": self.decision,
            "reason": self.reason,
            "rule": self.rule,
            "required_level": self.required_level,
            "granted_level": self.granted_level,
        }


class AuditLog:
    """Journal append-only. On n'efface ni ne modifie jamais une entrée."""

    def __init__(self) -> None:
        self._entries: list[AuditEntry] = []

    def append(self, entry: AuditEntry) -> AuditEntry:
        self._entries.append(entry)
        return entry

    def all(self) -> list[AuditEntry]:
        return list(self._entries)

    def tail(self, n: int = 20) -> list[AuditEntry]:
        return list(self._entries[-n:])

    def by_decision(self, decision: str) -> list[AuditEntry]:
        return [e for e in self._entries if e.decision == decision]

    def __len__(self) -> int:
        return len(self._entries)

    def __iter__(self) -> Iterator[AuditEntry]:
        return iter(list(self._entries))
