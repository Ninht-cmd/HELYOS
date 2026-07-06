# RFC-0008 — Plan Cash 90 jours & réconciliation des documents fondateurs externes

- **Statut** : Accepted
- **Date** : 2026-07-06
- **Auteur** : Le Conservateur
- **Principes ADN engagés** : 8 (honnêteté), 11 (un pas à la fois), 14 (frugalité), 16 (revenu d'abord)

## Contexte

Le fondateur a produit trois documents de référence hors repo (« Prompt Fondateur »,
« Plan Cash 90 Jours », « Spécification Noyau V1 », juillet 2026). Cette RFC les intègre
au Codex **sans les réécrire en silence** : ce qui est adopté est adopté explicitement,
ce qui diverge de l'existant est tracé.

## Décisions

### 1. Le Prompt Fondateur devient l'identité opérante

Canonisé dans [00_VISION/04_Prompt_Fondateur.md](../00_VISION/04_Prompt_Fondateur.md),
câblé dans le code via `persona.py` (Jarvis l'utilise comme préambule système du LLM
local). Il définit une doctrine de décision (patrimoine / temps / liberté), pas des
capacités.

### 2. Le Plan Cash 90 jours est LE plan opérationnel courant

Adopté tel quel. L'essentiel, opposable chaque semaine :

- **Offre** : Audit Flash (490 €) → Automatisation clé en main (1 500–3 000 €) →
  Abonnement (150–400 €/mois). Une seule niche pendant 90 jours.
- **Jalons** : 1er euro avant J30 (2 Audits Flash) · 1 Pack 2 signé à J60 ·
  1 000 €/mois récurrents à J90.
- **Règle de discipline n°1 : pas de développement du noyau avant J90, sauf si un
  client le paie.** Les clients sont livrés sur n8n/Make ; le kernel reste un outil
  interne (prospection, relances, suivi du fondateur — « client zéro »).
- Vendredi : 15 min de bilan, trois chiffres (prospects contactés, appels tenus,
  euros encaissés).

**Conséquence pour ce repo** : à partir de ce commit, le kernel est en **gel de
fonctionnalités** hors (a) corrections de bugs, (b) ce qui sert directement la
prospection/livraison du Plan Cash, (c) travail payé par un client.

### 3. La Spec Noyau V1 externe : convergences actées, divergences tracées

| Point de la spec externe | Existant kernel | Décision |
|---|---|---|
| « Le noyau ne fait aucun travail métier » | Agents séparés du kernel | ✅ Déjà conforme, principe gravé |
| Niveaux N0–N3 | A0–A5 + règles d'or | **A0–A5 reste la référence.** Mapping : N0≈A0 (lecture), N1≈A1-A2 (interne), N2≈GR-2 (externe réversible → validation), N3≈GR-1/GR-7 (irréversible/financier → validation à vie). Pas de double échelle. |
| Budgets par agent + blocage | Absent | `[CHANTIER]` V2 (déclencheur : 3 000 €/mois récurrents, comme la spec) |
| Mémoire double (journal append-only + connaissance consolidée) | EventBus + AuditLog + MemoryStore (journal partiel) | `[CHANTIER]` — la consolidation nocturne n'existe pas ; ne pas la revendiquer |
| Protocole agents MCP + manifeste YAML | Registre Python interne | `[CHANTIER]` V2+ — pertinent, non bloquant pour le Plan Cash |
| LLM orchestrateur = API frontier (Claude) | Ollama local (qwen3:8b) | **Divergence assumée en V1** : local d'abord = 0 € de coût fixe, conforme au budget ≤ 50 €/mois. L'API frontier deviendra pertinente quand un revenu la finance (arbitrage coût/qualité à J90). |
| Postgres + pgvector | SQLite/mémoire + embeddings Ollama | **Divergence assumée en V1** : zéro infra tant que le volume ne l'exige pas. Le port `MemoryStore` permet la migration sans réécriture. |
| Briefing matinal = file d'attente des N3 + anomalies | Absent | `[CHANTIER]` V2 — découle de la gouvernance existante (audit + REQUIRE_VALIDATION en attente), pas d'une feature nouvelle |

### 4. Portefeuille mis à jour

Le business n°4 (« HELYOS Services ») porte désormais les jalons du Plan Cash comme
tâches réelles, à la place des tâches génériques.

## Ce que cette RFC ne décide PAS

- Aucun revenu n'est promis : les chiffres du Plan (5 500–6 000 € T1) sont un **scénario**,
  pas un engagement.
- Le choix de la niche appartient au fondateur (décision humaine, définitive, semaine 1).
