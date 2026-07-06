# RFC-0009 — Connecteurs gouvernés (Shopify, GitHub, SMTP… et le refus TradingView)

- **Statut** : Accepted
- **Date** : 2026-07-06
- **Auteur** : Le Conservateur
- **Principes ADN engagés** : 3 (gouvernance), 8 (honnêteté), 14 (local d'abord)

## Résumé

`connectors/` : la couche qui relie HELYOS au monde réel, **entièrement derrière la
gouvernance**, en stdlib pur. Trois vérités structurantes :

1. **Lecture ≠ écriture.** Un sync (métriques réelles → portefeuille) est une action
   ANALYZE (A1), tracée sur le bus. Toute écriture vers l'extérieur (e-mail, publication)
   est EXTERNAL_SENSITIVE → **GR-2, validation humaine obligatoire, même en A5**.
2. **Un connecteur non branché le dit** : statut `not_configured` + la liste exacte des
   variables d'environnement à fournir. Pas de démo truquée.
3. **Un connecteur interdit le dit aussi** : TradingView apparaît `forbidden` avec la
   raison (ADR-0010 : pas d'API officielle, CGU §3 interdisent le trading automatisé →
   ban + juridique ; GR-7 : aucune transaction financière autonome, jamais). Le module
   `trading.py` n'appelle JAMAIS TradingView.

## Les connecteurs v1

| Connecteur | Type | État à la livraison | Sert à |
|---|---|---|---|
| **shopify** | lecture | à connecter (`HELYOS_SHOPIFY_SHOP/TOKEN`, app privée, scopes read_orders/read_products) | CA et commandes RÉELS de la boutique → portefeuille |
| **github** | lecture | **connecté** (API publique, zéro jeton) | étoiles/forks réels du repo → business open-source |
| **smtp** | écriture GR-2 | à connecter (`HELYOS_SMTP_HOST/PORT/USER/PASSWORD/FROM`) | **l'envoi réel des relances de factures** — la brique qui rend le v1 livrable (RFC-0006, étape 2) |
| **ollama** | intelligence | selon `HELYOS_LLM_BACKEND` | statut du LLM local |
| **tradingview** | — | **interdit** | afficher le refus et sa raison |
| stripe / n8n / nocodb / youtube | déclaratifs | à connecter | dire honnêtement ce qui manque, sans prétendre |

## Surface API

- `GET /connectors` — la carte des statuts (connected / not_configured / forbidden / error).
- `POST /connectors/sync` — sync **lecture seule**, soumis à la gouvernance (ANALYZE, A1),
  événement `connector.synced` ; un connecteur en échec ne casse pas les autres.
- Poste de pilotage : panneau « Intégrations » + bouton Synchroniser.

## Ce que cette RFC ne fait PAS

- Aucune écriture Shopify (publier des produits reste une action GR-2 hors connecteur v1).
- Aucun trading, aucun paiement : GR-7 est une frontière, pas un paramètre.
- Pas de MCP/manifeste YAML (spec externe V1) : viendra en V2+ (RFC-0008, jalons économiques).

## Conformité Plan Cash (RFC-0008)

Le SMTP gouverné sert directement la livraison client (relances) ; Shopify/GitHub sont de la
lecture de métriques pour le pilotage. Aucun de ces modules n'agrandit le noyau métier :
ce sont des ports remplaçables.
