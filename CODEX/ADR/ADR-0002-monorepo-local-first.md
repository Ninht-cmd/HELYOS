# ADR-0002 — Monorepo & local-first

- **Statut** : Accepted
- **Date** : 2026-06-28
- **Décideur(s)** : Le Conservateur
- **Principes ADN engagés** : 2, 3, 4, 5

## Contexte

HELYOS comporte un Codex, un Kernel, à terme de multiples modules et interfaces. Deux questions de structure : (1) un dépôt unique ou plusieurs ? (2) le cœur doit-il dépendre d'un cloud ?

## Décision

1. **Monorepo** : Codex, applications et déploiement vivent dans **un seul dépôt versionné**. Le Codex et le code évoluent ensemble, les liens entre eux sont vérifiables.
2. **Local-first** : le Kernel **démarre et passe ses tests sans aucun service externe** (bus mémoire + store mémoire). Les conteneurs (Postgres, Redis, Qdrant, Ollama, MinIO) sont des **augmentations opt-in**, jamais des prérequis du cœur.

## Conséquences

- **Positives** : cohérence Codex↔code, atomicité des changements, indépendance, démarrage trivial, résilience hors-ligne (ADN 2).
- **Négatives / coûts** : un monorepo grossit ; il faudra une discipline de structure (dossiers `apps/`, `CODEX/`, `deploy/`).
- **Chemin de sortie** : un module pourra être extrait en dépôt séparé s'il le justifie (modularité, ADN 4) — décision par ADR futur.

## Alternatives écartées

- *Multi-repos dès le départ* — surcoût de coordination prématuré pour un projet à un seul Conservateur.
- *Cœur dépendant du cloud* — violation frontale de l'ADN 2 (Local First).
