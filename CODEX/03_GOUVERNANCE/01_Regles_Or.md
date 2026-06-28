# Gouvernance — Les Règles d'Or

`v0.2` · Statut : **Stable & implémenté (interdits absolus)** → [`governance/policy.py`](../../apps/jarvis-kernel/src/jarvis_kernel/governance/policy.py)

---

Les règles d'or sont des **interdits absolus**. Elles ne dépendent pas du niveau d'autonomie : même un agent A5 ne peut pas les violer. Elles sont **codées et testées**, pas seulement écrites.

## Les trois interdits fondateurs (du Codex v0.1)

> **Jamais :**
> 1. **Suppression sans sauvegarde** — aucune donnée n'est détruite si une sauvegarde vérifiable n'existe pas.
> 2. **Action externe sensible sans validation** — aucun e-mail, publication, transaction, ou appel à un tiers sensible sans accord humain explicite.
> 3. **Auto-escalade des permissions** — aucun agent ne modifie son propre niveau d'autonomie ni n'élargit son propre périmètre.

## Tableau de référence

| # | Règle d'or | Déclencheur | Conséquence |
|---|------------|-------------|-------------|
| **GR-1** | Pas de suppression sans sauvegarde | action de type `delete` sans preuve de backup | **DENY** |
| **GR-2** | Pas d'action externe sensible sans validation | action `external` marquée *sensible* | **REQUIRE_VALIDATION** (au minimum) |
| **GR-3** | Pas d'auto-escalade | action qui modifie permissions/niveau de l'agent appelant | **DENY** |

## Corollaires (extensions tracées par RFC)

Ces règles dérivées appliquent l'esprit des trois interdits. Toute nouvelle règle d'or **doit** passer par une [RFC](../RFC/README.md).

- **GR-4 — Réversibilité par défaut** : une action irréversible non catégorisée est traitée comme A2+ (validation).
- **GR-5 — Traçabilité totale** : une action qui ne peut pas être journalisée ne peut pas être exécutée (ADN 6 & 16).
- **GR-6 — Souveraineté de la donnée** : aucune donnée du Conservateur ne quitte l'hôte local sans autorisation explicite (ADN 2).
- **GR-7 — Pas de finance autonome** : aucune transaction financière n'est jamais en A3+ ; elle reste **toujours** en validation humaine.

## Pourquoi coder les règles, pas seulement les écrire

Un principe écrit qu'aucun mécanisme n'applique est un **vœu**, pas une garantie. HELYOS exige que chaque règle d'or :

1. soit représentée dans le [PolicyEngine](../../apps/jarvis-kernel/src/jarvis_kernel/governance/policy.py),
2. provoque une décision **DENY** ou **REQUIRE_VALIDATION** vérifiable,
3. soit couverte par un **test** ([`tests/test_governance.py`](../../apps/jarvis-kernel/tests/test_governance.py)).

> C'est la différence entre une éthique *déclarée* et une éthique *exécutée*. HELYOS choisit la seconde.

## Le veto humain

Le Conservateur dispose d'un **droit de veto inconditionnel** sur toute action, à tout niveau, à tout moment. Aucun agent ne peut le contourner, le retarder au-delà d'un seuil, ou le désactiver. Ce droit est **architectural**, pas optionnel.
