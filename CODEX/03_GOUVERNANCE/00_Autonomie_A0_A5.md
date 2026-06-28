# Gouvernance — Autonomie graduée A0–A5

`v0.2` · Statut : **Stable & implémenté** → [`governance/autonomy.py`](../../apps/jarvis-kernel/src/jarvis_kernel/governance/autonomy.py)

---

L'autonomie d'HELYOS n'est **jamais binaire**. Elle est graduée sur 6 niveaux. Un agent opère **au niveau qui lui est accordé**, jamais au-dessus, et **ne peut pas s'auto-promouvoir** (règle d'or).

## L'échelle

| Niveau | Nom | L'agent peut… | Validation humaine |
|:------:|-----|---------------|:------------------:|
| **A0** | **Lecture** | Lire, observer, percevoir. Aucune écriture, aucune action. | — |
| **A1** | **Préparation** | Préparer, simuler, proposer un plan, rédiger un brouillon. Rien n'est appliqué. | — |
| **A2** | **Exécution avec validation** | Exécuter une action réelle **après** accord humain explicite, action par action. | ✅ obligatoire (chaque action) |
| **A3** | **Exécution faible risque** | Exécuter seul des actions **réversibles et à faible enjeu** (catégorisées au préalable). | ⬜ (audit a posteriori) |
| **A4** | **Gestion contrôlée** | Gérer un périmètre délimité de bout en bout, dans des garde-fous définis. | ⬜ (revue périodique) |
| **A5** | **Autonomie stratégique** | Agir sur la vision long terme, **uniquement** dans le cadre fixé par le Codex. | ⬜ (revue du Conservateur) |

## Règles de l'échelle

1. **Monotonie** : un niveau supérieur inclut les droits des niveaux inférieurs (A3 peut tout ce que A0–A2 permettent, dans son périmètre).
2. **Plafond explicite** : chaque agent et chaque session ont un **niveau plafond**. L'action requise > plafond ⇒ **refus** (ou passage en validation).
3. **Le défaut est bas** : en l'absence de mandat clair, le niveau est **A1** (préparer, ne pas agir).
4. **A5 n'est jamais le défaut** et ne s'applique qu'à des décisions explicitement cadrées par le Codex.

## Comment une action est classée

Le [PolicyEngine](../../apps/jarvis-kernel/src/jarvis_kernel/governance/policy.py) associe à chaque **type d'action** un **niveau requis** + d'éventuelles **règles d'or**. Exemples :

| Action | Niveau requis | Règle d'or associée |
|--------|:-------------:|---------------------|
| Lire un fichier / une base | A0 | — |
| Résumer, analyser, proposer un plan | A1 | — |
| Écrire/modifier un fichier local | A2 | Sauvegarde préalable |
| Envoyer un e-mail / poster en ligne | A2 | Action externe sensible → validation |
| Renommer dans un dossier de travail | A3 | Réversible & faible risque |
| Supprimer des données | A2+ | **Jamais sans sauvegarde** |
| Exécuter une transaction financière | A2 (jamais auto) | Toujours validation humaine |
| Modifier ses propres permissions | **Interdit** | Pas d'auto-escalade |

> La table complète et faisant autorité vit **dans le code** ([`policy.py`](../../apps/jarvis-kernel/src/jarvis_kernel/governance/policy.py)) et est **testée**. Ce document en est le miroir lisible.

## Décision de gouvernance

Pour toute action, le PolicyEngine renvoie l'une de trois décisions :

- **ALLOW** — niveau suffisant, aucune règle d'or violée → l'action part sur le bus.
- **REQUIRE_VALIDATION** — niveau insuffisant *mais* rattrapable par un accord humain → mise en attente du veto.
- **DENY** — règle d'or violée ou action interdite → refus, tracé, non rattrapable sans changement de contexte.

Chaque décision est **journalisée** ([AuditLog](../../apps/jarvis-kernel/src/jarvis_kernel/governance/audit.py)) — application directe de l'ADN 16.

→ Les interdits absolus : [Règles d'or](01_Regles_Or.md)
