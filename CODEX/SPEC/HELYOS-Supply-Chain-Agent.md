# HELYOS Supply Chain — couche Agent (données réelles + proposition gouvernée)

- **Statut** : Accepted · **Date** : 2026-08-02
- **Implémentation** : `world/domains/supply_chain_agent.py` + `data/receptions.csv` · **Tests** : `test_supply_chain_agent.py` (4)

---

## 1. Le fossé adressé (critique légitime)

Le Supply Chain OS calculait « le point de commande doit passer de 109 à 159 » — un **moteur de
décision spécialisé**, pas un **agent**. Un agent dirait plutôt : *« le fournisseur dérive, j'ai
identifié un alternatif, comparé, préparé la demande de devis ; j'attends ta validation avant envoi. »*
Et rien ne prouvait, depuis les captures, que les données n'étaient pas codées en dur.

Cette couche ferme **deux** morceaux (honnêtement, pas tout le JARVIS) :

## 2. (A) Données réelles — connecteur CSV

`read_receptions_csv(path)` lit un fichier réel (`data/receptions.csv`, colonnes `date_reception,
fournisseur, delai_jours`) que **l'utilisateur remplace par ses propres réceptions**. Plus de données
codées en dur : la démo lit **31 lignes du fichier**.

## 3. (B) Comportement d'agent — proposition gouvernée

`advise(target, rows, …, governance, granted)` enchaîne :
1. apprendre le délai réel de **chaque** fournisseur (régression bayésienne) ;
2. détecter la **dérive** du fournisseur cible ;
3. identifier un **fournisseur alternatif** plus rapide **présent dans les données** ;
4. chiffrer l'**impact** (point de commande, coût) ;
5. **proposer** des actions et **soumettre l'action externe** (demande de devis) à la
   **gouvernance A0–A5** → `REQUIRE_VALIDATION` (GR-2). L'agent **propose et attend la validation** ;
   il n'envoie jamais seul — même à A5 (les règles d'or priment).

## 4. Preuve (sur `data/receptions.csv`, réel)

```
31 réceptions lues du fichier.
Délais appris : FRN-07 14.31 j (±0.30, 25 récep.) · FRN-12 7.24 j (±0.60, 6 récep.)
Agent : « FRN-07 dérive 9 → 14.31 j. J'ai identifié un alternatif plus rapide : FRN-12 (~7.24 j).
         Impact : point de commande 109.2 → 163.7 u. J'ai préparé la demande de devis ;
         action externe → require_validation (GR-2) : j'attends ta validation avant envoi. »
Action externe soumise à GovernanceService → REQUIRE_VALIDATION (GR-2).
```

## 5. Ce que ça ferme — et ce qui reste (honnête)

- **Fermé** : (A) données **réelles** remplaçables (CSV) ; (B) **raisonnement multi-étapes** finissant en
  **proposition supervisée**, branché sur la **vraie gouvernance** (pas un jouet).
- **Reste** (l'ambition large, non résolue) : le JARVIS **multi-domaines** et **multi-connecteurs**
  (ERP, CRM, Gmail, navigateur, CAD…) connecté **en permanence** à des sources réelles, planifiant et
  exécutant de bout en bout sur des dizaines d'outils. Un connecteur CSV sur un domaine n'est pas ça.
- **Terminologie** : « Business OS » est une **métaphore** (orchestration de modèles/règles/décisions/
  connecteurs), pas un OS au sens informatique (processus, mémoire, périphériques).

Voir [[HELYOS-Supply-Chain-OS-v1.0]], [[HELYOS-Model-Governance-v1.0]], [[ADR-0003]] (gouvernance).
