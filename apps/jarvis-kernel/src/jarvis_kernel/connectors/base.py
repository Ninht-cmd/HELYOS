"""Socle des connecteurs : statut honnête + transport injectable (testable sans réseau)."""

from __future__ import annotations

import json
import os
import urllib.request
from collections.abc import Callable
from dataclasses import asdict, dataclass, field

# Un transport prend (url, headers) et rend le JSON décodé. Injectable pour les tests.
Transport = Callable[[str, dict], dict]


def default_transport(url: str, headers: dict | None = None) -> dict:
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req, timeout=10) as resp:  # noqa: S310 (URL construite en dur)
        return json.loads(resp.read().decode("utf-8"))


@dataclass(frozen=True)
class ConnectorStatus:
    """Ce que l'UI affiche. `status` ∈ connected | not_configured | forbidden | error."""

    name: str
    kind: str
    status: str
    detail: str = ""
    requires: str = ""          # ce qu'il faut fournir pour passer à « connected »

    def to_dict(self) -> dict:
        return asdict(self)


class Connector:
    """Interface minimale. `sync` est optionnel (lecture seule, jamais d'écriture monde)."""

    name: str = "connector"
    kind: str = "generic"

    def status(self) -> ConnectorStatus:  # pragma: no cover - abstrait
        raise NotImplementedError

    # sync(portfolio) -> dict résumé, ou None si non configuré. Lecture SEULE.
    sync = None


@dataclass
class EnvConnector(Connector):
    """Connecteur déclaratif : « connecté » si ses variables d'env sont présentes.

    Sert à dire honnêtement ce qui existe (n8n, Stripe, YouTube…) sans prétendre
    à une intégration que le code n'a pas encore.
    """

    name: str = "env"
    kind: str = "generic"
    env_vars: tuple[str, ...] = field(default_factory=tuple)
    requires: str = ""
    note: str = ""

    def status(self) -> ConnectorStatus:
        missing = [v for v in self.env_vars if not os.environ.get(v)]
        if missing:
            return ConnectorStatus(self.name, self.kind, "not_configured",
                                   detail=self.note, requires=self.requires)
        return ConnectorStatus(self.name, self.kind, "connected", detail=self.note)
