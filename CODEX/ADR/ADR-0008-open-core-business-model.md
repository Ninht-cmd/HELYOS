# ADR-0008 — Modèle économique : Open Core

- **Statut** : Accepted
- **Date** : 2026-06-29
- **Décideur(s)** : Le Conservateur
- **Principes ADN engagés** : 3, 13, 14

## Contexte

« Open ou fermé ? » est un faux binaire. HELYOS doit **être ouvert** (adoption, ADN 3) **et**
**financer sa R&D** (ADN 13, boucle économique). La question utile est : *quel est l'actif le
plus précieux à protéger ?*

## Décision

**HELYOS adopte un modèle Open Core.**

1. **Cœur ouvert (AGPL-3.0, [ADR-0005](ADR-0005-licence.md))** : kernel, **gouvernance A0–A5**,
   bus, API de base, SDK, mémoire de base. C'est le bien commun qui crée l'adoption et la confiance
   (une gouvernance auditable *doit* être inspectable).
2. **Modules commerciaux (propriétaires, dépôt privé `helyos-pro`)** : agents spécialisés
   (juridique, finance, industrie…), mémoire distribuée avancée, orchestration multi-IA,
   dashboard entreprise, déploiement 1-clic, support & mises à jour prioritaires.
3. **L'actif protégé (les « joyaux »)** : la **gouvernance avancée**, la **mémoire** (et le RAG
   à l'échelle), les **agents spécialisés**, et à terme les **données/modèles entraînés**. On ouvre
   le reste, on monétise et on protège **ça**. Détail : [Frontière open-core](../05_ECONOMIE/02_Frontiere_Open_Core.md).
4. **Trois sources de revenus** : (a) **licence commerciale** du cœur (dual-licensing AGPL),
   (b) **modules Pro/Enterprise**, (c) **SaaS/cloud** géré + support. Voir [business model](../05_ECONOMIE/01_Business_Model.md).
5. **Règle de frontière** : une fonctionnalité va dans le cœur si elle sert l'**adoption, la
   confiance ou la gouvernance** ; elle va en Pro si elle crée un **avantage opérationnel
   spécialisé** pour une organisation. En cas de doute → cœur (l'ouverture est le défaut, ADN 3).

## Conséquences

- **Positives** : adoption + confiance (cœur ouvert et auditable) **et** revenus (Pro/SaaS/licence) ;
  alignement direct avec la boucle économique (revenus → R&D).
- **Négatives / coûts** : maintenir **deux dépôts** (public/privé) et une **frontière nette** ;
  risque de « course en avant » des forks → atténué par l'AGPL + la valeur des modules + le SaaS.
- **Chemin de sortie** : la frontière open/Pro est révisable par ADR ; on peut **ouvrir** un module
  Pro plus tard (jamais l'inverse sans précaution — on n'« referme » pas du code déjà publié).

## Alternatives écartées

- *100 % ouvert* — pas de protection de l'actif clé, financement R&D fragile.
- *100 % fermé* — perd l'adoption, la confiance (gouvernance non inspectable) et l'esprit ADN 3.
- *Privé d'abord, ouvrir plus tard* — option valable (construire l'avance en privé), mais le
  Conservateur a choisi d'ouvrir le cœur **maintenant** pour amorcer adoption + crédibilité ;
  l'avance se protège via les modules Pro et les données/modèles, pas via la fermeture du cœur.
