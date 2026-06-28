# Module — RuView (Wi-Fi Sensing)

`v0.2` · Statut : **🔬 R&D / exploration** · Niveau d'autonomie : **A0–A1** (perception seule)

---

## Idée

Transformer un signal **Wi-Fi** existant en **capteur de présence et de mouvement**, sans caméra ni micro. En analysant les variations du canal radio (**CSI — Channel State Information**) ou simplement le RSSI, on détecte la présence humaine, le mouvement, voire la respiration, dans une pièce — un « radar » logiciel à partir d'un routeur ordinaire.

> *Origine de l'idée :* veille fondatrice (« This open source code just turned a router into a radar system »). RuView en est la déclinaison HELYOS, **cadrée par la gouvernance**.

## Pourquoi c'est aligné avec HELYOS

| Critère d'admission | Réponse |
|---|---|
| **Friction supprimée** | Perception de contexte (présence/activité) **sans caméra** → vie privée préservée, coût matériel quasi nul. |
| **Local-first** | 100 % local : le traitement du signal reste sur l'hôte. Aucune donnée ne sort (GR-6). |
| **Gouvernance** | Perception pure → **A0/A1**. RuView **n'agit pas** ; il publie des événements `presence.*` sur le bus. |
| **Réversibilité** | Module débranchable ; aucun état critique. |
| **Observabilité** | Métriques : taux de détection, faux positifs, latence. |

## Architecture (esquisse)

```
 Routeur / carte Wi-Fi (CSI)
        │  capture brute
        ▼
 ┌──────────────────┐   features   ┌─────────────────┐   events    ┌──────────┐
 │ Capteur CSI/RSSI │─────────────▶│ Traitement      │────────────▶│ EventBus │
 │ (driver/edge)    │              │ signal + modèle │ presence.*  │ (Kernel) │
 └──────────────────┘              │ (détection)     │             └──────────┘
                                   └─────────────────┘
```

Événements publiés : `presence.detected`, `presence.cleared`, `motion.detected`, `room.occupancy.changed`.

## Garde-fous éthiques (non négociables)

RuView est une technologie de **détection sensible**. Le Codex impose :

1. **Consentement & souveraineté** — uniquement dans un espace contrôlé par le Conservateur (GR-6). Jamais de surveillance de tiers non consentants.
2. **Pas d'identification** — RuView détecte *présence/mouvement*, **pas** l'identité des personnes.
3. **Local & éphémère** — données de signal traitées localement, non exportées, rétention minimale.
4. **Transparence** — l'activation de RuView est explicite et visible (jamais silencieuse).

> Toute extension (ex. estimation de respiration, comptage de personnes) requiert une **RFC dédiée** réévaluant ces garde-fous.

## Pistes techniques (à valider en Labs)

- Cartes/firmwares exposant le CSI (ex. ESP32-CSI, Atheros/Intel CSI tools, Nexmon).
- Pré-traitement : filtrage, normalisation, fenêtrage temporel.
- Détection : seuils statistiques (No-AI) **d'abord**, modèle appris **ensuite** seulement si le gain est mesurable (ADN 14).

## Prochaines étapes

1. RFC `RuView-001` : périmètre, matériel cible, garde-fous détaillés.
2. Prototype Labs : capture CSI + détection présence par seuil (mode No-AI).
3. Intégration bus : publier `presence.*`, mesurer faux positifs.
