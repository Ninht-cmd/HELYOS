# ADR — Architecture Decision Records

Un **ADR** capture une décision technique structurante : le **contexte**, la **décision**, et ses **conséquences**. Application directe de l'ADN 16 (*aucune décision importante ne reste dans une conversation*).

## Règles

- Un ADR est **immuable** une fois `Accepted`. On ne le réécrit pas : on l'amende via un nouvel ADR qui le **remplace** (`Superseded by ADR-XXXX`).
- Numérotation continue, jamais réutilisée.
- Statuts : `Proposed` → `Accepted` → (`Deprecated` | `Superseded`).
- Gabarit : [`_template.md`](_template.md).

## Index

| ADR | Titre | Statut |
|-----|-------|--------|
| [0001](ADR-0001-codex-source-of-truth.md) | Le Codex est la source de vérité | Accepted |
| [0002](ADR-0002-monorepo-local-first.md) | Monorepo & local-first | Accepted |
| [0003](ADR-0003-governance-kernel.md) | La gouvernance vit dans le Kernel | Accepted |
| [0004](ADR-0004-event-bus.md) | Bus d'événements comme colonne vertébrale | Accepted |
| [0005](ADR-0005-licence.md) | Choix de licence | Proposed |
