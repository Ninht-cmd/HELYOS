# HELYOS — Planificateur + Orchestrateur multi-agents (couche cognitive)

- **Statut** : Accepted · **Date** : 2026-08-02
- **Implémentation** : `world/planner.py` · **Tests** : `test_planner.py` (4)
- **Livre les briques** : #2 (Planner), #3 (Orchestrateur multi-agents), #8 (Explication des décisions)

---

## 1. Le keystone manquant

HELYOS avait des agents spécialisés (supply chain) bien gouvernés, mais **rien ne les reliait**.
Cette couche est l'architecture cognitive qui transforme un **objectif** en **plan coordonné, expliqué
et gouverné**.

## 2. Mécanisme

1. **Planner** (`decompose`) : un objectif → sous-objectifs (méthodes HTN-lite). Ex. « réduire les coûts
   de 15 % » → analyser coûts (finance) · identifier dérives (supply) · comparer alternatifs (supply) ·
   simuler l'impact (supply) · proposer & contacter (général, **effet externe**).
2. **Orchestrateur** (`run`) : route chaque sous-objectif vers l'**agent compétent** (registre de
   `Capability`), exécute, et **agrège**.
3. **Explication** (brique #8) : chaque étape porte **résultat + confiance + sources**.
4. **Gouvernance** : les étapes à effet externe passent en `REQUIRE_VALIDATION` (GR-2), même à A5.

## 3. Preuve (sur données réelles + gouvernance réelle)

```
OBJECTIF : Réduire les coûts de 15%
1. [finance]      Coût 120000 € ; −15% ⇒ 18000 € à retrancher          conf 0.90  · Domaine Finance
2. [supply_chain] FRN-07 délai 14.31 j (25 récep.) ; alternatif FRN-12  conf 0.93  · data/receptions.csv
3-4. [supply_chain] (comparaison / simulation)                          conf 0.93
5. [général]      Proposer & contacter — REQUIRE_VALIDATION (GR-2)      conf 0.55
Confiance globale 0.85 · en attente de validation : oui
```

## 4. Portée honnête

- Décomposition par **méthodes/patrons**, pas un planificateur **appris** (ni LLM ni HTN complet).
- **3 agents** enregistrés ; les handlers sont **grossiers** (l'agent supply-chain renvoie une analyse
  similaire pour ses sous-objectifs analyser/comparer/simuler — à différencier).
- La **collaboration** est un routage + agrégation, pas encore une vraie négociation inter-agents.
- Restent (route JARVIS) : connecteurs temps réel multiples, mémoire long terme unifiée, vision
  multimodale, dizaines d'agents, interface Jarvis complète.

## 5. Ce que ça change

HELYOS passe d'**un agent spécialisé** à un **système qui décompose un objectif, coordonne plusieurs
agents et rend un plan expliqué + gouverné**. C'est la première brique de l'IA générale orientée
entreprise — le reste s'y branche (chaque nouvel agent = une `Capability` de plus).

Voir [[HELYOS-Supply-Chain-Agent]], [[HELYOS-Model-Governance-v1.0]], [[DD-0001]] (Phase B : planification).
