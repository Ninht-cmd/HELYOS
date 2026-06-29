# RFC-0003 — Arbitrage du nom (HELYOS vs helyOS ; « Jarvis » saturé)

- **Statut** : In Review *(décision du Conservateur)*
- **Date** : 2026-06-29
- **Auteur** : Le Conservateur (proposé par l'IA)
- **Principes ADN engagés** : 1, 10, 12

## Résumé

Trancher l'identité de marque avant toute publication, à cause de **deux collisions**
documentées dans l'[état de l'art](../08_ECOSYSTEME/00_Etat_de_lart.md).

## Problème / friction

1. **HELYOS vs helyOS** — un projet open-source **homonyme** (Fraunhofer IVI) existe
   **dans notre domaine** (orchestration de robots/véhicules). Risque de confusion réelle,
   problèmes SEO, ambiguïté juridique potentielle.
2. **« Jarvis »** — nom **saturé** (NVIDIA Riva ex-Jarvis, Microsoft JARVIS/HuggingGPT,
   dizaines d'assistants). Ne pourra jamais porter la différenciation.

**Pourquoi maintenant ?** Le coût d'un changement de nom **croît avec le temps** (ADN 12).
À v0.3, non public, il est quasi nul. Après publication, il devient douloureux.

## Options

| # | Option | Pour | Contre |
|---|--------|------|--------|
| **1** | **Garder HELYOS**, se différencier par la gouvernance + le domaine (OS d'intelligence *personnelle* ≠ flottes de véhicules) | Zéro coût, attachement préservé | Confusion/SEO persistants avec helyOS |
| **2** | **Ajuster la marque** (typographie/orthographe distinctive, ex. un dérivé de « Helye ») en gardant l'esprit | Lève la collision, garde la racine *Helye* | Léger coût de rebrand |
| **3** | **Garder HELYOS pour l'OS**, mais **renommer la couche incarnée** (« Jarvis » → nom propre non saturé) | Règle la saturation « Jarvis » | Deux décisions de nom |
| **4** | **Nouveau nom complet** | Table rase, distinctif | Coût émotionnel/identitaire élevé |

## Recommandation (à valider)

**Option 1 + 3** : garder **HELYOS** (le différenciateur est la *gouvernance*, pas le nom ;
le domaine diffère de helyOS) **et** réserver « Jarvis » à un usage **interne/conceptuel**,
en choisissant à terme un nom propre distinct pour la couche incarnée publique.
→ Décision **réversible** tant que non publié ; à reconsidérer avant un lancement public.

## Critères de décision

Distinctivité · risque de collision de domaine · disponibilité (marque/domaine/handles) ·
SEO · attachement du Conservateur · **coût de changement** (croissant).

## Questions ouvertes (pour le Conservateur)

- Quel poids donnes-tu à l'attachement au nom « HELYOS » vs le risque de collision ?
- Le dépôt public initial doit-il être **privé** (le temps de trancher) ou **public** d'emblée ?

> Tant que cette RFC est `In Review`, recommandation opérationnelle : **dépôt GitHub privé**.
