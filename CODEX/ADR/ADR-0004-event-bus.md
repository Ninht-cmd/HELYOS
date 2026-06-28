# ADR-0004 — Bus d'événements comme colonne vertébrale

- **Statut** : Accepted
- **Date** : 2026-06-28
- **Décideur(s)** : Le Conservateur
- **Principes ADN engagés** : 4, 6, 9

## Contexte

Les composants (perception, mémoire, agents, gouvernance, modules comme RuView) doivent communiquer sans se coupler directement. Un couplage en étoile rigidifierait le système et trahirait la modularité (ADN 4).

## Décision

Le **bus d'événements** (pub/sub) est la **colonne vertébrale** du Kernel. Les composants publient et s'abonnent à des **événements** typés (`presence.detected`, `intent.received`, `governance.decided`, `action.executed`…) plutôt que de s'appeler directement.

- Implémentation par défaut : **bus en mémoire** (zéro dépendance, local-first).
- Implémentation cible : **Redis** (distribué) derrière la **même interface** — substituable sans changer les composants.

## Conséquences

- **Positives** : découplage fort, observabilité native (tout est un flux d'événements, ADN 6), extensibilité (un module s'abonne sans modifier le cœur), intelligence composée (ADN 9).
- **Négatives / coûts** : raisonnement asynchrone, besoin de tracer les flux pour les comprendre (résolu par l'observabilité).
- **Chemin de sortie** : l'interface `EventBus` isole l'implémentation ; passer mémoire→Redis→autre est local.

## Alternatives écartées

- *Appels directs entre composants* — couplage fort, non extensible.
- *File de messages lourde dès le départ (Kafka…)* — surdimensionné pour la phase actuelle (ADN 11, complexité maîtrisée).
