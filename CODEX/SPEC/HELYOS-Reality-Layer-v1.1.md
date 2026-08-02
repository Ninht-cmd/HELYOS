# HELYOS Reality Layer v1.1 — l'organisme au-dessus du noyau

- **Statut** : Accepted (moteur implémenté + testé) · **Date** : 2026-08-02
- **Implémentation** : `world/reality.py` + extension `world/ontology.py` · **Tests** : `test_reality.py` (5)
- **Étend** : HELYOS-Ontology-v1.0, RFC-0019, DD-0001

---

## 1. Ce que la Reality Layer ajoute

L'ontologie v1.0 donnait les **objets** du monde. La Reality Layer ajoute ce sans quoi on ne peut ni
planifier ni réagir : les **ressources**, les **objectifs structurés**, les **événements** qui propagent
le changement, la **boucle réactive** (événement → décision), et le premier étage de la **simulation
multi-pas (H=N)**. C'est le passage « représentation du monde » → « organisme ».

## 2. Ontologie v1.1 — 10 types de première classe ajoutés (≈ 26 au total)

`Goal` · `Project` · `Process` · `Resource` · `Contract` · `Event` · `Material` · `Technology` ·
`Location` · `Risk`, plus 10 relations (`has_goal, part_of_project, consumes, governed_by, affected_by,
located_in, made_of, realizes, exposes, runs`). Chaque attribut numérique reste une **croyance μ±σ**.

## 3. Les quatre briques (implémentées, chiffrées)

**Resource Model** — `resource_pool(graph)`, `feasible(graph, needs)`. Les `Resource` (kind =
financial/human/material/digital) donnent un pool pondéré par disponibilité ; `feasible` renvoie les
**manques**. *Sans ressources, pas de plan* : une action non couverte est écartée.

**Goal System** — `Goal` est une entité (priorité, horizon, budget, risque) avec des **métriques cibles**
(`meta['targets'] = {clé_de_croyance: cible}`) ; `goal_attainment()` renvoie l'atteinte ∈ [0,1].

**Event System** — `apply_event(graph, interventions)` : un événement est une intervention `do(x=v)` qui
**se propage** dans le graphe causal (réutilise `simulate`), incertitude comprise.

**Boucle réactive + H=N** — `respond(graph, company, options)` classe les réponses par ΔU d'entreprise en
écartant les infaisables ; `rollout(graph, company, steps)` applique une **séquence** et renvoie la
trajectoire d'utilité (rollout déterministe multi-pas).

## 4. Preuve (bout en bout, testé)

```
AVANT      marge 78.7% · atteinte objectif 0.87 · U +0.111
ÉVÉNEMENT  prix fournisseur ×2
APRÈS      marge 57.3% · atteinte objectif 0.64 · U +0.059   (ΔU −0.052)
DÉCISION   1. Monter le prix +20%  ΔU +0.001
           2. Renégocier −20%      ΔU −0.010
           3. Embaucher 5 ing.     INFAISABLE (manque 5 humains)   ← modèle de ressources
```

## 5. Positionnement sur la roadmap du fondateur (statut honnête)

| Palier | Contenu visé | Statut réel |
|---|---|---|
| **v1.1 Reality Layer** | Ontologie complète · Knowledge Graph · **Resource Model** · **Goal System** · **Event System** | ✅ **Fait** (moteur + tests) |
| v1.3 Simulation Engine | Monte-Carlo · scénarios · propagation d'incertitude | 🟡 **Amorcé** : rollout **déterministe** H=N + propagation σ. Le **Monte-Carlo à N futurs** reste à faire. |
| v1.2 Causal Intelligence | Causal graph · règles économiques/industrielles/financières | 🟡 Les dérivations sont **posées à la main**, pas des **règles causales apprises**. |
| v1.4 Opportunity Engine | Business Factory · découverte · validation marché | ⬜ Le type `Opportunity` + `score` existent ; le **moteur** de découverte non. |
| v2.0 Domain OS | Finance/Trading/Engineering/Manufacturing/Research OS | ⬜ Non construits (au-delà des outils actuels : RSI/SMA, STL, codegen). |

## 6. Ce que v1.1 N'EST PAS (annoncé, pas caché)

- Le rollout est **déterministe et énuméré**, pas un échantillonnage Monte-Carlo de 1000 futurs (v1.3).
- Les fonctions de dérivation (les « lois » causales) sont **écrites à la main**, pas apprises des
  résultats (Phase C DD-0001).
- Le graphe n'est pas **peuplé** automatiquement par les connecteurs (travail continu).
- `company_utility` est une scalarisation heuristique par entité, non calibrée.

## 7. Prochain palier recommandé

Deux chemins complémentaires, au choix :
1. **v1.3 — Simulation Monte-Carlo** : tirer N trajectoires en échantillonnant les croyances (μ±σ) et les
   événements probabilistes, agréger en distribution d'utilité + probabilité de succès. C'est le vrai
   passage H=1 → *« 1000 futurs → trajectoire optimale »*.
2. **Peuplement par connecteurs** : GitHub/marché/Shopify écrivent des entités réelles → le graphe cesse
   d'être un bac de démonstration.

Voir [[HELYOS-Ontology-v1.0]], [[RFC-0019]], [[DD-0001]], [[HELYOS-Architecture-Specification-v1.0]].
