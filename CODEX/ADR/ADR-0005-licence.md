# ADR-0005 — Choix de licence

- **Statut** : Proposed
- **Date** : 2026-06-28
- **Décideur(s)** : Le Conservateur
- **Principes ADN engagés** : 3, 12, 13

## Contexte

HELYOS est **open-source-first** (ADN 3) mais doit aussi **financer la R&D** via des produits (ADN 13) et durer plusieurs générations (ADN 12). Le choix de licence doit concilier ouverture, protection contre l'appropriation non-réciproque, et capacité de monétisation.

## Décision (proposée — à trancher)

Plusieurs options sur la table, **non encore arbitrées** :

| Option | Avantage | Risque |
|--------|----------|--------|
| **Apache-2.0** | Adoption maximale, clause brevets | Permet l'appropriation propriétaire sans réciprocité |
| **AGPL-3.0** | Réciprocité forte (cloud inclus) | Peut freiner certains usages commerciaux tiers |
| **Double licence** (AGPL + commerciale) | Ouverture **et** monétisation | Complexité de gestion |
| **Source-available** (BSL → open après N ans) | Protège la monétisation initiale | Pas « open-source » au sens OSI |

## Conséquences

- À compléter une fois la décision prise. Cet ADR sera **remplacé** par une version `Accepted`.

## Prochaine étape

Ouvrir une **RFC** comparant licences à la lumière de la [boucle économique](../05_ECONOMIE/00_Boucle_Economique.md) et de la stratégie Ventures.
