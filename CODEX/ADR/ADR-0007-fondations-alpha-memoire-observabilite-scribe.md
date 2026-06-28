# ADR-0007 — Fondations Alpha (memoire, observabilite, scribe)

- **Statut** : Proposed
- **Date** : 2026-06-29
- **Décideur(s)** : Le Conservateur
- **Principes ADN engagés** : 6, 8, 14, 16
- **Rédigé par** : ScribeAgent (proposé ; à valider par le Conservateur)

## Contexte

Le jalon Pré-Alpha (kernel v0) est franchi. Pour entrer en Alpha, trois fondations manquaient : une mémoire qui survit au redémarrage, une observabilité distribuée, et un premier agent utile démontrant le flux gouverné.

## Décision

1) Mémoire persistante derrière MemoryStore : SQLite par défaut (local, zéro service), adaptateurs Postgres et Qdrant optionnels, plus une mémoire vectorielle locale de repli. 2) Observabilité : OpenTelemetry -> OTLP/Langfuse, optionnel et no-op si absent ; le flux de gouvernance est instrumenté. 3) ScribeAgent (A2, RFC-0002) : transforme une décision en ADR, l'écriture passant par la gouvernance.

## Conséquences

- Le Codex devient interrogeable (mémoire) au service de l'ADN 15.
- L'ADN 16 devient mesurable (décisions tracées automatiquement).
- Le cœur reste Local First : toutes les briques lourdes sont optionnelles.
- Cet ADR a été écrit par le ScribeAgent lui-même (preuve vivante).
