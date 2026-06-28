# C4 — Niveau 1 : Contexte système

`v0.2` · Statut : **Stable**

---

Qui interagit avec HELYOS, et avec quels systèmes externes ?

```
                         ┌───────────────────────────┐
                         │       LE CONSERVATEUR      │
                         │   (fondateur / utilisateur)│
                         └─────────────┬─────────────┘
                                       │ voix · texte · vision · validation A2+
                                       ▼
        ┌──────────────────────────────────────────────────────────┐
        │                          HELYOS                           │
        │   Système d'exploitation de l'intelligence personnelle.   │
        │   Comprend · Décide · Agit · Transmet — sous gouvernance.  │
        └───┬───────────────┬───────────────┬──────────────┬────────┘
            │               │               │              │
            ▼               ▼               ▼              ▼
   ┌──────────────┐ ┌──────────────┐ ┌─────────────┐ ┌──────────────┐
   │ LLM locaux   │ │ APIs cloud   │ │ Outils &    │ │ Capteurs &   │
   │ (Ollama)     │ │ (opt-in,     │ │ services    │ │ périphériques│
   │              │ │  si requis)  │ │ (MCP, web)  │ │ (cam, micro, │
   │              │ │              │ │             │ │  robot/edge) │
   └──────────────┘ └──────────────┘ └─────────────┘ └──────────────┘
```

## Acteurs

| Acteur | Rôle | Niveau d'autorité |
|--------|------|-------------------|
| **Le Conservateur** | Fondateur, propriétaire de la donnée, décideur final. Donne le cap, valide les actions A2+. | Souverain |
| **Les IA (agents)** | Architectes/ingénieurs spécialisés. Proposent, exécutent sous mandat. | Délégué (A0–A5) |

## Systèmes externes

| Système | Usage | Principe ADN engagé |
|---------|-------|---------------------|
| **LLM locaux (Ollama)** | Raisonnement par défaut, hors-ligne | Local First (2) |
| **APIs cloud** | Uniquement si nécessaire et autorisé | Non-dépendance — opt-in |
| **Outils / MCP / Web** | Action sur le monde (Playwright, connecteurs MCP) | Gouvernance (action = A2+) |
| **Capteurs / Edge / Robot** | Perception et action physique | Modularité (4) |

## Frontières

- **Tout le cœur fonctionne en local.** Le retrait d'Internet dégrade les capacités externes mais **n'arrête pas** le système (principe 2).
- **Toute sortie vers un système externe sensible** traverse la [gouvernance](../03_GOUVERNANCE/00_Autonomie_A0_A5.md) (jamais d'action externe sensible sans validation).

→ Niveau suivant : [Conteneurs](02_C4_Containers.md)
