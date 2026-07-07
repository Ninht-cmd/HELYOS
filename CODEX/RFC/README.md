# RFC — Request For Comments

Une **RFC** est une proposition **structurante** mise en discussion *avant* d'être tranchée. Là où un [ADR](../ADR/README.md) **acte** une décision, une RFC **explore et propose**. Une RFC acceptée donne souvent naissance à un ou plusieurs ADR.

## Cycle de vie

```
Draft  →  In Review  →  Accepted  →  (donne lieu à ADR / implémentation)
                     ↘  Rejected  (tracé, avec la raison)
```

## Quand ouvrir une RFC

- Nouveau **module** (obligatoire — voir [admission d'un module](../04_MODULES/00_Overview.md)).
- Nouvelle **règle d'or** ou évolution de la gouvernance.
- Changement de **stack** majeur.
- Toute idée fondatrice qui dépasse une simple décision technique.

## Index

| RFC | Titre | Statut |
|-----|-------|--------|
| [0001](RFC-0001-jarvis-kernel-v0.md) | Périmètre du Kernel Jarvis v0 | Accepted |
| [0002](RFC-0002-scribe-agent.md) | ScribeAgent : le premier agent utile | Accepted |
| [0003](RFC-0003-arbitrage-du-nom.md) | Arbitrage du nom (HELYOS vs helyOS ; « Jarvis ») | In Review |
| [0004](RFC-0004-orchestration-agents.md) | Orchestration d'agents composés (sous gouvernance) | Accepted |
| [0005](RFC-0005-business-scaffolder.md) | BusinessScaffolder — « HELYOS crée des business » (gouverné, honnête) | Accepted |
| [0006](RFC-0006-helyos-v1-relance-factures.md) | HELYOS v1 — agent de relance de factures (1ʳᵉ tâche payante) | Accepted |
| [0007](RFC-0007-jarvis-couche-conversationnelle.md) | Jarvis — couche conversationnelle unifiée + interface honnête | Accepted |
| [0008](RFC-0008-plan-cash-90-jours.md) | Plan Cash 90 jours & réconciliation des documents fondateurs | Accepted |
| [0009](RFC-0009-connecteurs-gouvernes.md) | Connecteurs gouvernés (Shopify, GitHub, SMTP — TradingView interdit) | Accepted |
| [0010](RFC-0010-analyste-marche-et-mcp.md) | Analyste de marché gouverné (GR-7) & serveur MCP (accès Claude) | Accepted |

Gabarit : [`_template.md`](_template.md).
