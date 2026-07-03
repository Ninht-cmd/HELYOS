# RFC-0005 — BusinessScaffolder : « HELYOS crée des business », version crédible

- **Statut** : Accepted
- **Date** : 2026-07-03
- **Auteur** : Le Conservateur
- **Principes ADN engagés** : 8, 9, 14, 16

## Résumé

Un agent gouverné qui génère le **squelette** d'un business (idées produits + copie +
pages requises + checklist de lancement), pour incarner honnêtement l'idée « HELYOS crée
des business » — sans la survendre.

## Problème / friction

Créer un business demande des heures de travail répétitif (structure, fiches produits,
pages légales, checklist). C'est exactement le type de friction que l'ADN veut supprimer
(« transformer le temps en actifs », ADN 14).

## Proposition

`agents/business_scaffolder.py` :
- `scaffold(name, niche, model)` → un `BusinessPlan` (produits via `LLMPort`, pages requises,
  checklist humaine, disclaimer). Niveau **A1** (préparation) : ça *génère un artefact*, ça
  n'agit pas sur le monde.
- `propose_publish(plan, target)` → **action externe sensible** → **GR-2 : validation humaine
  obligatoire, même en A5**. C'est le cœur : HELYOS crée le scaffold, mais publier sur une
  plateforme réelle est **gouverné**.
- Copie déterministe avec `StubLLM` (tests) ; réelle avec `OllamaLLM` (démontré : qwen3:8b).

## Honnêteté (non négociable)

> **Un scaffold n'est PAS un revenu.** Le module génère la coquille ; les ventes dépendent de
> la fabrication, du paiement, du trafic, du marché et du capital — **hors périmètre**. Un champ
> `disclaimer` le dit explicitement dans chaque plan. On ne prétend JAMAIS que « HELYOS génère
> de l'argent tout seul ».

## Gouvernance

Génération = A1 (aucun effet monde). Toute publication/exécution externe = passe par le
PolicyEngine → REQUIRE_VALIDATION (GR-2). Chaque plan est mémorisé (namespace `business`) et
la décision journalisée (audit).

## Monétisation (le vrai chemin)

Ce module devient une **capacité vendable** (open-core Pro / SaaS) : d'autres paient pour
scaffolder+opérer leurs business sous gouvernance. Le revenu vient de la **vente de l'outil**,
pas d'une IA qui mint de l'argent. Horizon : produit + vente (mois), pas instantané.

## Alternatives

- *Agent « autonome » qui lance et fait tourner un business rentable seul* — rejeté : n'existe
  pas, ne marche pas (fantasme Auto-GPT). On construit la version honnête et gouvernée.

## Questions ouvertes

- Connecteurs réels gouvernés (Shopify `create-product`, pages) derrière A2 → « publier » devient
  une exécution réelle validée, pas seulement une proposition.
- Templates au-delà du print-on-demand (services, contenu) par RFC.
