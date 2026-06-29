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
| [0005](ADR-0005-licence.md) | Choix de licence — **AGPL-3.0 + dual-licensing** | Accepted |
| [0006](ADR-0006-fusion-jarvis-helyos-stacks.md) | Fusion Jarvis × HELYOS & alignement stacks externes | Accepted |
| [0007](ADR-0007-fondations-alpha-memoire-observabilite-scribe.md) | Fondations Alpha (mémoire, observabilité, Scribe) — *écrit par le ScribeAgent* | Proposed |
| [0008](ADR-0008-open-core-business-model.md) | Modèle économique : **Open Core** | Accepted |
| [0009](ADR-0009-conformite-legale.md) | Conformité légale & PI (marques, CLA, disclaimers, RGPD) | Accepted |
