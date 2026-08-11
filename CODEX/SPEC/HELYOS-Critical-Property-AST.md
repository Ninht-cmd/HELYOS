# HELYOS — CriticalPropertyAnalyzer (découverte AST des propriétés critiques)

- **Statut** : Accepted · **Date** : 2026-08-09
- **Implémentation** : `world/critical_property.py`
- **Tests** : `test_critical_property.py` (7)
- **Convergence** : `critical_targets(props)` alimente `DiffCoverageAnalyzer` et le moteur de mutation

---

## 1. Le saut : de « ligne 140 » à « propriété »

Avant, la criticité venait de marqueurs textuels + du chemin `governance/`. Un GR-2 déplacé
dans `world/toolbus.py` échappait. On transforme désormais l'**AST en propriétés de contrôle** :

```
ligne 140 = critique        →        CP-MV-001 = « toute action externe sensible doit
                                       atteindre REQUIRE_VALIDATION avant exécution »
```

`analyze_source/analyze_file` lit la STRUCTURE, pas des tokens :
- **décision de sécurité** = référence à l'enum `Decision.REQUIRE_VALIDATION`/`DENY`
  (`ast.Attribute`/`ast.Name` en position *Load*), **pas** une chaîne `"REQUIRE_VALIDATION"`
  ni un commentaire (absents de l'AST), ni un enum mentionné dans une **f-string** de log ;
- **garde sensible** = un `if` dont le test mentionne `sensitive`/`validated`/`has_backup`/
  `EXTERNAL_SENSITIVE`/`FINANCIAL`/`SELF_PERMISSION`/comparaison d'autonomie — avec un
  mini data-flow intraprocédural (`is_external = … or action.sensitive` propage la sensibilité) ;
- **gate** = un appel `.submit()/.evaluate()` ;
- **effet externe** = un appel `execute/run/send/write/delete/…`.

## 2. Trois genres de propriété

- `mandatory_validation` — une décision `REQUIRE_VALIDATION`/`DENY` atteinte **sous une garde
  sensible**. Preuve = structure de flot (`if <garde> → <décision>`). CRITICAL.
- `governance_gate` — un appel `.submit()/.evaluate()` qui protège la suite. HIGH.
- `critical_bypass` — un **effet externe sous garde sensible SANS** gate ni décision. CRITICAL.

## 3. `CriticalProperty` (prêt pour l'interprocédural)

```
CriticalProperty(id, kind, sources[…], guards[…], protected_effect, required_outcome,
                 criticality, location, confidence, evidence[…], line)
```
`sources` est déjà une **liste** : une propriété pourra traverser plusieurs fichiers quand le
CFG interprocédural arrivera. Ce brick fait l'analyse **intraprocédurale**.

## 4. Cinq cas d'acceptation — tous verts

```
CAS 1  governance/policy.py réel      → 4 propriétés découvertes (GR-2, GR-7 REQUIRE_VALIDATION ;
                                        GR-1, GR-3 DENY), gardes = control-flow réel
CAS 2  même logique dans world/toolbus.py → mandatory_validation + governance_gate détectés
                                        (INDÉPENDANT du chemin)
CAS 3  "REQUIRE_VALIDATION" en string / commentaire → AUCUNE propriété
CAS 4  effet sensible sans gouvernance → CRITICAL_BYPASS_FOUND
CAS 5  mutation de la ligne dérivée de la propriété → tuée par le test ciblé (mutation_score 1.0)
```

**Scan du dépôt réel** : 5 `mandatory_validation`, 44 `governance_gate` sur 21 fichiers
(dont `toolbus.py`, `planner.py`, `service.py`…), **0 bypass** dans le code bien gouverné.

## 5. Convergence des briques

`critical_targets(props)` renvoie `(fichier, ligne, criticité)` : les propriétés deviennent les
cibles de la couverture de diff (exécutée ?), des sondes comportementales (vérifiée ?) et de la
mutation (corruption détectée ?), qui alimentent `ChangeAssurance`. La criticité n'est plus
déclarée par un chemin ; elle est **découverte** par la structure.

## 6. Portée honnête & suite

- Analyse **intraprocédurale** : une garde et son effet doivent être dans la même fonction. Une
  chaîne Agent → ToolBus → GovernanceService → Policy → REQUIRE_VALIDATION n'est pas encore
  suivie de bout en bout.
- Détection par **motifs d'appel** (`.submit`, `.execute`) : robuste mais nommage-dépendante.
- Un survivant d'f-string est écarté ; d'autres faux positifs fins restent possibles (tolérés
  côté prudence).

**Prochain brick** — **CFG + data-flow interprocédural** : suivre un chemin depuis une entrée
contrôlée par un agent jusqu'à une action externe sensible, et prouver qu'aucun chemin
n'échappe à la gouvernance. HELYOS vérifiera alors ses **garanties de sécurité
architecturales**, pas seulement son code ligne par ligne.

Voir [[HELYOS-Mutation-Testing]], [[HELYOS-Diff-Coverage]], [[HELYOS-CI-Incident-Intelligence]].
