# Contribuer à HELYOS

> Lis le [Codex](CODEX/README.md) **avant** de contribuer (ADN 15). Le Codex prime sur le code.

## Les règles d'or de la contribution

1. **Le Codex est la vérité.** Si ton code contredit le Codex, c'est le code qui a tort — ou alors ouvre une [RFC](CODEX/RFC/_template.md) pour faire évoluer le Codex.
2. **Aucune décision importante ne reste dans une conversation** (ADN 16). Elle devient un [ADR](CODEX/ADR/_template.md) ou une RFC.
3. **Une fonctionnalité supprime une friction mesurable** (ADN 14), sinon elle n'entre pas.
4. **Zéro dette technique volontaire** (ADN 5).

## Flux type

```
Idée structurante ──▶ RFC (discussion) ──▶ ADR (décision) ──▶ Code + Tests ──▶ CHANGELOG
```

Pour un changement de code :

1. **Avant** : la décision est-elle tracée (ADR/RFC) ? Sinon, trace-la.
2. **Tests d'abord** pour toute règle de gouvernance (une règle non testée n'existe pas — [ADR-0003](CODEX/ADR/ADR-0003-governance-kernel.md)).
3. **Local-first** : le cœur ne doit pas gagner de dépendance externe obligatoire.
4. **Observable** : toute action laisse une trace (ADN 6).
5. **Lance la suite** : `./scripts/dev.ps1 test` (ou `dev.sh`). Tout doit être vert.
6. **Mets à jour** le [CHANGELOG](CHANGELOG.md) et, si pertinent, le Codex.

## Style de code (Kernel)

- Python ≥ 3.11, typage explicite, docstrings en français reliant au Codex.
- Le **cœur** (`kernel/`, `governance/`, `memory/`, `agents/`) ne dépend **que de la stdlib**.
- Les dépendances lourdes (FastAPI, etc.) restent dans des couches optionnelles.
- Toute nouvelle dépendance = un **ADR** (justification + alternative open-source + sortie).

## Gouvernance des modules

Un nouveau module **doit** passer le [test d'admission](CODEX/04_MODULES/00_Overview.md) (friction, gouvernance A0–A5, local-first, réversibilité, observabilité) via une RFC, avant tout code.
