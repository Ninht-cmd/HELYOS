# HELYOS — Mémoire long terme unifiée v1.0 (brique #1)

- **Statut** : Accepted · **Date** : 2026-08-02
- **Implémentation** : `world/memory_store.py` + orchestrateur · **Tests** : `test_memory.py` (3)
- **Critère d'acceptation** : ✅ un correctif refusé n'est pas re-proposé (la mémoire change le comportement).

---

## 1. Le problème

HELYOS produit des objectifs, observations réelles, plans, décisions, validations/refus, résultats.
Sans mémoire propre, l'orchestrateur **repart de zéro** à chaque exécution. Une mémoire décorative
(juste du RAG vectoriel) ne suffit pas.

## 2. Deux couches (jamais une simple base vectorielle)

- **Relationnelle** : la vérité structurée — objectif, date, agent, action, **statut**, source,
  confiance, gouvernance, validation humaine, résultat réel, liens.
- **Vectorielle** (cosinus sac-de-mots) : retrouver des situations **similaires par le sens**.

**Cinq objets** seulement : `MemoryEvent`, `Episode`, `DecisionRecord`, `OutcomeRecord`, `MemoryLink`.

## 3. Séparer « ce qui s'est passé » de « ce qu'HELYOS croit »

Statuts obligatoires : `observed · inferred · proposed · validated · executed · confirmed ·
superseded · rejected`. Une proposition d'agent ne devient **jamais** automatiquement une vérité.
Bonne mémoire : *« 2026-08-08 supply_chain_agent a estimé FRN-12 plus rapide. Source: receptions.csv.
Confiance 0.93. État: inferred. »* — pas *« FRN-12 est meilleur »*.

## 4. Le cycle complet + le Planner qui interroge la mémoire AVANT

`observation → objectif → plan → décision → validation/refus → action → résultat → évaluation →
apprentissage → mémoire → objectif suivant`. L'orchestrateur appelle `memory.retrieve(objectif)`
**avant** de planifier (« qu'a-t-on essayé ? validé ? refusé ? »), injecte le rappel dans le contexte,
puis **enregistre** chaque événement/décision.

## 5. Preuve — le critère d'acceptation (testé + démontré)

```
RUN #1  « Analyse HELYOS et propose une amélioration »
   → propose « corriger cache LLM (perf) » (status proposed)   mémoire : has_history=False
   → l'humain REFUSE (raison : trop risqué)                     → DecisionRecord = rejected

RUN #2  « Analyse encore HELYOS »
   mémoire retrouvée : has_history=True ; refusés : ['corriger cache LLM (perf)']
   → « Le correctif "cache LLM (perf)" avait été refusé ; je ne le re-propose pas.
      Je propose plutôt "docstrings API (doc)". »
```

La mémoire **n'est pas décorative** : elle modifie réellement la décision suivante.

## 6. Portée honnête

- Vectoriel = **cosinus sac-de-mots** local (déterministe) — remplaçable par des embeddings réels
  (Qdrant) sans changer les appelants.
- L'**évaluation/apprentissage** à partir des `OutcomeRecord` (comparer résultat observé vs attendu
  pour ajuster les futurs plans) est **amorcée** (objets présents) mais pas encore bouclée dans le Planner.
- Le rappel est par similarité + entités ; pas encore de raisonnement temporel fin (« quels faits ont changé »).

## 7. Suite (ordre adopté)

#1 mémoire unifiée **(faite)** → #4 GitHub-API réel (OAuth) → Gmail/Calendar → agents spécialisés
(Dev/Finance/CRM/Cyber) → multimodal → interface Jarvis. La prochaine grosse victoire n'est pas
l'apparence, mais qu'HELYOS **se souvienne et adapte** — c'est acquis pour le refus ; reste à boucler
l'apprentissage des **résultats**.

Voir [[HELYOS-Planner-Orchestrator]], [[HELYOS-ToolBus-Connectors]], [[HELYOS-Model-Governance-v1.0]].
