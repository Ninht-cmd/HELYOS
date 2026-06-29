# ADR-0005 — Choix de licence

- **Statut** : Accepted
- **Date** : 2026-06-29
- **Décideur(s)** : Le Conservateur
- **Principes ADN engagés** : 3, 12, 13

## Contexte

HELYOS est **open-source-first** (ADN 3) mais doit **financer la R&D** (ADN 13) et durer
(ADN 12). Le projet adopte un modèle **open-core** ([ADR-0008](ADR-0008-open-core-business-model.md)) :
un **cœur ouvert** (kernel, gouvernance, API de base, SDK) et des **modules commerciaux**
(agents spécialisés, mémoire distribuée avancée, orchestration multi-IA, dashboard
entreprise, déploiement 1-clic, support prioritaire). Ambition : trajectoire scale
(cf. [business model](../05_ECONOMIE/01_Business_Model.md)).

## Décision

1. **Cœur open source sous AGPL-3.0.** Le copyleft fort protège contre l'exploitation
   en SaaS fermé par un concurrent (toute modification servie sur le réseau doit être
   rouverte). Fichier [`LICENSE`](../../LICENSE) à la racine = texte AGPL-3.0 verbatim.
2. **Double licence (dual-licensing).** Le Conservateur **détient le copyright** du cœur,
   ce qui permet de **vendre une licence commerciale** à qui ne peut/veut pas se conformer
   à l'AGPL (entreprises, intégration propriétaire). C'est le levier de monétisation premier.
3. **Modules commerciaux** = licence propriétaire, dans un **dépôt privé séparé** (`helyos-pro`),
   jamais sous AGPL. La frontière est définie dans [02_Frontiere_Open_Core](../05_ECONOMIE/02_Frontiere_Open_Core.md).
4. **CLA** (Contributor License Agreement) requis pour toute contribution externe future,
   afin de préserver la capacité de double licence.

## Conséquences

- **Positives** : ouverture réelle (ADN 3), **protection** contre les forks SaaS fermés,
  monétisation par licence commerciale **et** par modules Pro, copyright maîtrisé.
- **Négatives / coûts** : l'AGPL peut freiner certains usages d'entreprise → c'est *voulu*
  (ça crée la demande de licence commerciale). Nécessite un CLA et une rigueur sur la
  provenance du code (pas de code AGPL tiers dans les modules propriétaires).
- **Chemin de sortie** : détenant le copyright, le Conservateur peut **re-licencier** le
  cœur à l'avenir (ex. ajouter une exception) sans dépendre de tiers (tant qu'il n'y a pas
  de contributeurs externes sans CLA).

## Alternatives écartées

- *Apache-2.0* — adoption maximale mais **aucune protection** contre un SaaS fermé concurrent ;
  incohérent avec une ambition de revenus à l'échelle.
- *Tout propriétaire* — contraire à l'ADN 3, et prive de l'effet d'écosystème/adoption.
- *MIT/BSD* — idem Apache, sans clause brevets.

## Décisions liées
- [ADR-0008](ADR-0008-open-core-business-model.md) — modèle open-core.
- [Business model](../05_ECONOMIE/01_Business_Model.md) · [Frontière open-core](../05_ECONOMIE/02_Frontiere_Open_Core.md).
