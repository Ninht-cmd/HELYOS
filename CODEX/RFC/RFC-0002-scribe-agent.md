# RFC-0002 — ScribeAgent : le premier agent utile

- **Statut** : Accepted
- **Date** : 2026-06-28
- **Auteur** : Le Conservateur
- **Principes ADN engagés** : 8, 14, 16

## Résumé

Un agent qui transforme une **décision** en un **fichier ADR** correctement formaté,
l'écriture passant par la gouvernance (A2).

## Problème / friction

Deux frictions **mesurables** :
1. **Décisions perdues** — des choix importants restent dans des conversations et
   s'évaporent (le Dossier Fondateur v0.1 déplorait exactement cela).
2. **Boilerplate ADR fastidieux** — formater un ADR à la main décourage de le faire.

**Métriques** : nombre d'ADR capturés / semaine ; temps moyen pour produire un ADR
(objectif : < 1 min via le Scribe vs plusieurs minutes à la main). Le respect de
l'ADN 16 devient **mesurable** (taux de décisions tracées).

## Proposition

`ScribeAgent` (`apps/jarvis-kernel/.../agents/scribe.py`) :
- `propose(...)` → une `Action` de type `WRITE_LOCAL` (créer `CODEX/ADR/ADR-XXXX-slug.md`).
- `draft_adr(...)` → soumet l'action à la gouvernance ; **si ALLOW**, écrit le fichier,
  mémorise la décision (namespace `decisions`) et émet `scribe.adr_written`.
- `index_codex(...)` → bonus : indexe le Codex (lecture A0) dans la mémoire persistante,
  au service de l'ADN 15 (« relire le Codex avant toute stratégie »).

## Gouvernance

- Écrire un fichier = **A2**. Sans niveau A2 (ni validation), l'ADR **n'est pas écrit** :
  l'action reste `REQUIRE_VALIDATION`. Démonstration vivante du flux gouverné.
- Indexer le Codex = **A0** (lecture), tout de même **audité**.

## Local-first & réversibilité

100 % local. Un ADR mal rédigé se corrige par un nouvel ADR (le format ADR est
lui-même réversible par conception). Aucun service externe requis.

## Observabilité

Spans `scribe.draft_adr` / `scribe.index_codex` ; événements sur le bus ; entrées d'audit
pour chaque action soumise. Métriques de friction stockables en mémoire.

## Alternatives

- *Écrire les ADR à la main* — c'est la friction qu'on supprime.
- *Génération hors gouvernance* — rejeté : même un acte « utile » comme écrire un fichier
  doit passer par la gouvernance (cohérence de l'invariant, [ADR-0003](../ADR/ADR-0003-governance-kernel.md)).

## Questions ouvertes

- Étendre le Scribe aux **RFC** et aux entrées de **CHANGELOG** ?
- Brancher la recherche **vectorielle** (Qdrant) sur l'index du Codex pour un vrai « relire le Codex » sémantique.
