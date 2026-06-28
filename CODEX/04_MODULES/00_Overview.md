# Modules HELYOS — Vue d'ensemble

`v0.2` · Statut : **Catalogue ouvert (chaque module = une RFC)**

---

Un **module** est un domaine fonctionnel branché sur le Kernel via le [bus d'événements](../02_ARCHITECTURE/03_C4_Components_Kernel.md) et soumis à la [gouvernance](../03_GOUVERNANCE/00_Autonomie_A0_A5.md). Modularité absolue (ADN 4) : un module s'ajoute ou se retire **sans toucher au cœur**.

## Catalogue

| Module | Objet | Niveau d'autonomie typique | Statut | Fiche |
|--------|-------|:--------------------------:|:------:|-------|
| **RuView (Wi-Fi sensing)** | Perception de présence/mouvement via signaux Wi-Fi (CSI), sans caméra | A0–A1 (perception) | 🔬 R&D | [fiche](01_RuView_WiFi_Sensing.md) |
| **Cybersécurité** | Posture défensive (Blue) & tests offensifs autorisés (Red) | A0–A2 (jamais d'action offensive sans validation) | 🔧 cadrage | [fiche](02_Cybersecurite.md) |
| **Vision** | Perception visuelle, lecture d'écran, suivi | A0–A1 | ⬜ RFC | — |
| **Robotique** | Pont edge/robot, actionneurs physiques | A2+ (action physique = validation) | ⬜ horizon | — |
| **Automatisation** | Orchestration de workflows, RPA, MCP | A2–A3 | ⬜ RFC | — |
| **Trading** | Veille marché, signaux, exécution via connecteurs/MCP | **A2 max, jamais auto** (GR-7) | ⬜ RFC | — |
| **Création de contenu** | Texte, image, audio, vidéo (outils IA) | A1–A2 | ⬜ RFC | — |
| **Infrastructure** | Déploiement, observabilité, sauvegardes | A2–A4 (périmètre délimité) | 🔧 partiel | [deploy](../../deploy/) |
| **Documentation** | Codex vivant, génération de docs (type OS industriel) | A1–A2 | ✅ ce Codex | [CODEX](../README.md) |

## Règle d'admission d'un module

Avant d'écrire une ligne de code, un module doit répondre **par écrit (RFC)** à :

1. **Friction** — quelle friction mesurable supprime-t-il ? (ADN 14)
2. **Gouvernance** — quels types d'actions, à quels niveaux A0–A5, avec quelles règles d'or ?
3. **Local-first** — fonctionne-t-il sans cloud ? Sinon, pourquoi (opt-in justifié) ?
4. **Réversibilité** — quel est le chemin de sortie / désactivation ?
5. **Observabilité** — quelles métriques prouvent qu'il marche et qu'il sert ?

> Un module qui ne passe pas ce test n'entre pas dans HELYOS. C'est l'ADN qui filtre, pas l'enthousiasme.
