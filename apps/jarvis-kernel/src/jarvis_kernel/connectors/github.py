"""Connecteur GitHub — étoiles/forks réels du repo public (API publique, zéro jeton).

Alimente le business ``opensource``. Fonctionne immédiatement : le repo HELYOS
est public. ``HELYOS_GITHUB_REPO`` pour pointer ailleurs (défaut : Ninht-cmd/HELYOS).
"""

from __future__ import annotations

import os

from ..business.portfolio import BusinessPortfolio
from .base import Connector, ConnectorStatus, Transport, default_transport


class GitHubConnector(Connector):
    name = "github"
    kind = "opensource"

    def __init__(self, repo: str | None = None, transport: Transport | None = None) -> None:
        self.repo = repo or os.environ.get("HELYOS_GITHUB_REPO", "Ninht-cmd/HELYOS")
        self.transport = transport or default_transport

    def status(self) -> ConnectorStatus:
        return ConnectorStatus(self.name, self.kind, "connected",
                               detail=f"{self.repo} · API publique, lecture seule")

    def sync(self, portfolio: BusinessPortfolio) -> dict | None:
        data = self.transport(f"https://api.github.com/repos/{self.repo}",
                              {"Accept": "application/vnd.github+json",
                               "User-Agent": "helyos-kernel"})
        stars = int(data.get("stargazers_count", 0))
        forks = int(data.get("forks_count", 0))
        target = next((b for b in portfolio.list() if b.kind == "opensource"), None)
        if target is None:
            return {"stars": stars, "forks": forks, "applied_to": None}
        portfolio.set_metric(target.name, "stars", stars)
        portfolio.set_metric(target.name, "forks", forks)
        return {"stars": stars, "forks": forks, "applied_to": target.name}
