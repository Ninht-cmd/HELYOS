# ADR-0001 — Le Codex est la source de vérité

- **Statut** : Accepted
- **Date** : 2026-06-28
- **Décideur(s)** : Le Conservateur
- **Principes ADN engagés** : 1, 10, 15, 16

## Contexte

Le projet a démarré dans des conversations avec des modèles d'IA. Le Dossier Fondateur v0.1 le dit explicitement : *« Je ne peux pas reconstituer à 100 % les anciennes conversations supprimées. »* La mémoire d'un modèle est volatile et non faisant-autorité. Il faut un point d'ancrage stable, indépendant de tout outil et de tout modèle.

## Décision

Le **Codex** (dossier `CODEX/`) est la **source de vérité unique** d'HELYOS. Il est versionné (git). Aucun modèle, aucune conversation, aucun bout de code ne prime sur lui. La hiérarchie d'autorité est :

```
ADN > Vision/Mission > ADR acceptés > Architecture > Code
```

Toute décision importante **doit** rejoindre le Codex sous forme d'ADR ou de RFC.

## Conséquences

- **Positives** : continuité multi-générationnelle, indépendance vis-à-vis des modèles, auditabilité, onboarding rapide de tout futur contributeur (humain ou IA).
- **Négatives / coûts** : discipline d'écriture exigée ; un travail non documenté « n'existe pas ».
- **Chemin de sortie** : aucun souhaité — c'est un principe fondateur (ADN 16).

## Alternatives écartées

- *Se fier à la mémoire des modèles* — volatile, non auditable, non transmissible.
- *Documentation ad hoc dans le code seulement* — le code est trop bas niveau pour porter la vision (la Mission stipule : le Codex prime sur le code).
