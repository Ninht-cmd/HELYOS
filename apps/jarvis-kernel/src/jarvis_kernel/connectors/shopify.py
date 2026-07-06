"""Connecteur Shopify — lecture seule vers le portefeuille.

Configuration (app privée « custom app » dans l'admin Shopify, scopes
``read_orders`` + ``read_products``) :
- ``HELYOS_SHOPIFY_SHOP``  : ex. ``kgqc06-yq.myshopify.com``
- ``HELYOS_SHOPIFY_TOKEN`` : jeton Admin API (``shpat_…``)

Le sync alimente le business de type ``ecommerce`` avec les CHIFFRES RÉELS
(commandes payées, CA). Aucune écriture vers Shopify ici : publier/modifier la
boutique reste une action externe sensible (GR-2) hors de ce connecteur.
"""

from __future__ import annotations

import os

from ..business.portfolio import BusinessPortfolio
from .base import Connector, ConnectorStatus, Transport, default_transport

_API = "2024-10"


class ShopifyConnector(Connector):
    name = "shopify"
    kind = "ecommerce"

    def __init__(self, shop: str | None = None, token: str | None = None,
                 transport: Transport | None = None) -> None:
        self.shop = shop or os.environ.get("HELYOS_SHOPIFY_SHOP", "")
        self.token = token or os.environ.get("HELYOS_SHOPIFY_TOKEN", "")
        self.transport = transport or default_transport

    @property
    def configured(self) -> bool:
        return bool(self.shop and self.token)

    def status(self) -> ConnectorStatus:
        if not self.configured:
            return ConnectorStatus(
                self.name, self.kind, "not_configured",
                detail="lecture des commandes/CA réels de la boutique",
                requires="HELYOS_SHOPIFY_SHOP + HELYOS_SHOPIFY_TOKEN "
                         "(app privée, scopes read_orders/read_products)")
        return ConnectorStatus(self.name, self.kind, "connected",
                               detail=f"{self.shop} · lecture seule")

    def _get(self, path: str) -> dict:
        return self.transport(
            f"https://{self.shop}/admin/api/{_API}/{path}",
            {"X-Shopify-Access-Token": self.token},
        )

    def sync(self, portfolio: BusinessPortfolio) -> dict | None:
        """Lecture seule -> métriques réelles sur le business ecommerce."""
        if not self.configured:
            return None
        count = self._get("orders/count.json?status=any").get("count", 0)
        paid = self._get(
            "orders.json?status=any&financial_status=paid&limit=250&fields=total_price"
        ).get("orders", [])
        revenue = round(sum(float(o.get("total_price", 0) or 0) for o in paid), 2)

        target = next((b for b in portfolio.list() if b.kind == "ecommerce"), None)
        if target is None:
            return {"orders": count, "revenue_eur": revenue, "applied_to": None}
        portfolio.set_metric(target.name, "commandes", count)
        portfolio.set_metric(target.name, "revenue_eur", revenue)
        # honnêteté : au-delà de 250 commandes payées, le CA affiché est partiel
        if len(paid) == 250:
            portfolio.set_metric(target.name, "revenue_note", "CA partiel (>250 commandes)")
        return {"orders": count, "revenue_eur": revenue, "applied_to": target.name}
