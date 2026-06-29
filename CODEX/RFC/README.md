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

Gabarit : [`_template.md`](_template.md).
