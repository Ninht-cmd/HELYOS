# ADR-0006 — Fusion Jarvis × HELYOS et alignement sur des stacks externes

- **Statut** : Accepted
- **Date** : 2026-06-28
- **Décideur(s)** : Le Conservateur
- **Principes ADN engagés** : 1, 3, 4, 9, 11

## Contexte

Une revue de l'existant ([Related Work](../08_ECOSYSTEME/00_Etat_de_lart.md)) montre que :
1. Des briques **mûres et open** couvrent déjà perception, parole, orchestration d'agents
   et exécution locale (NVIDIA Isaac GR00T, Riva, NeMo Agent Toolkit ; Stanford OpenJarvis).
2. **Aucune** ne place au centre une **gouvernance graduée auditée** — l'angle propre d'HELYOS.
3. Deux **collisions de noms** existent : **helyOS** (Fraunhofer, orchestration de véhicules)
   et **Jarvis** (NVIDIA Riva, Microsoft HuggingGPT, multiples assistants).

## Décision

1. **Fusion architecturale** : Jarvis cesse d'être un « produit à côté » et devient la
   **couche d'incarnation gouvernée** d'HELYOS (perception, voix, action, robotique).
   *HELYOS = cerveau gouverné ; Jarvis = corps.* Voir [Fusion](../02_ARCHITECTURE/05_Fusion_HELYOS_Jarvis.md).
2. **Ne pas reconstruire l'existant** (ADN 11) : on **adopte derrière des interfaces** —
   Voice→Riva, Robotique/Vision→Isaac GR00T (sim d'abord), multi-agents→NeMo Toolkit+LangGraph,
   mémoire→Postgres/Qdrant — chacun **substituable** (non-dépendance).
3. **Construire ce qui manque** : le **kernel de gouvernance** (« Governed Embodiment »),
   le Codex, l'observabilité gouvernée. C'est notre contribution originale.
4. **Invariant de gouvernance** : toute capacité incarnée passe par la gouvernance A0–A5 ;
   l'action physique réelle est **A2 minimum** + règles d'or. Non négociable.

## Conséquences

- **Positives** : focalisation sur le différenciateur (gouvernance), vélocité (on réutilise
  des stacks PhD-grade), trajectoire robotique crédible (Isaac/Jetson), indépendance préservée.
- **Négatives / coûts** : surface d'intégration large ; chaque stack externe = une RFC + des
  ports d'abstraction à maintenir. Dépendance GPU/NVIDIA pour la robotique avancée (atténuée
  par « simulation d'abord » et interfaces).
- **Chemin de sortie** : chaque brique étant derrière une interface (`VoicePort`,
  `ActuatorPort`, `PerceptionPort`, `MemoryStore`, LiteLLM), elle est remplaçable.

## Question ouverte (non tranchée ici)

**Le nom.** HELYOS entre en collision avec **helyOS** (Fraunhofer) *dans le même domaine*
(robotique/orchestration), et « Jarvis » est saturé. Options : garder HELYOS et se
différencier par la gouvernance ; ajuster la typographie/marque ; réserver « Jarvis » à
un usage interne. → **À traiter par une RFC dédiée** avant toute communication publique.

## Alternatives écartées

- *Tout construire en propre (perception, parole, VLA)* — irréaliste et contraire à l'ADN 11.
- *Se lier à un fournisseur unique (full NVIDIA, sans interfaces)* — viole la non-dépendance.
