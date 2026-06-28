# Jarvis — Le produit

`v0.2` · Statut : **Kernel implémenté, sous-systèmes à venir**

---

> **Jarvis est un produit d'HELYOS, pas l'entreprise.** C'est l'intelligence opérationnelle incarnée, inspirée de l'esprit de « Jarvis » (Iron Man), mais fondée sur des technologies **réelles, ouvertes, modulaires et durables**.

## Les 7 sous-systèmes

| Sous-système | Rôle | Statut v0.2 | Stack cible |
|--------------|------|:-----------:|-------------|
| **Kernel** | Bus, gouvernance, mémoire, registre d'agents | ✅ v0 implémenté | FastAPI |
| **Memory** | Mémoire court terme (Redis) + long terme vectorielle (Qdrant) + RAG | 🔧 interface posée | Postgres, Qdrant, LlamaIndex/Haystack |
| **Voice** | STT / TTS, conversation parlée | ⬜ à spécifier (RFC) | (à décider) |
| **Vision** | Perception visuelle, suivi, lecture d'écran | ⬜ à spécifier | MediaPipe, OpenCV, Playwright |
| **Business** | Agents métier (contenu, trading, ops) | ⬜ à spécifier | LangGraph + MCP |
| **Research** | Veille, synthèse, recherche autonome | ⬜ à spécifier | LangGraph, LlamaIndex |
| **Robotics** | Pont vers l'edge / le robot | ⬜ horizon roadmap | (à décider) |

## La boucle OODA

Jarvis raisonne selon une boucle **OODA** (Observe → Orient → Decide → Act), entièrement instrumentée et **gouvernée à l'étape « Act »** :

```
   Observe ─────▶ Orient ─────▶ Decide ─────▶ Act
   (perception)  (mémoire+   (raisonne-   (gouvernance
    capteurs,     contexte,    ment LLM,    A0–A5 → outils)
    events)       RAG)         agents)          │
      ▲                                          │
      └────────────── feedback / trace ──────────┘
```

L'étape **Act** ne s'exécute jamais sans passer par le [PolicyEngine](03_C4_Components_Kernel.md). C'est ce qui distingue Jarvis d'un agent autonome naïf : **l'action est un privilège gouverné, pas un acquis**.

## Mode « No-AI »

Conformément aux idées fondatrices, Jarvis prévoit un **mode No-AI** : un chemin déterministe (scripts, règles, automatisations) qui fonctionne **sans appel à un modèle**. Utile pour :
- les tâches critiques où l'on veut un comportement reproductible,
- la résilience (panne de modèle),
- l'audit (comportement explicable à 100 %).

→ Ce mode est une exigence de l'ADN 6 (observable) et 11 (complexité maîtrisée).

## Agents : le principe d'intelligence composée

Plutôt qu'un méga-modèle, Jarvis **compose** des agents spécialisés (ADN 9), chacun :
- déclarant le **niveau d'autonomie** qu'il requiert,
- enregistré dans l'`AgentRegistry`,
- orchestré (à terme) via **LangGraph**,
- traçable individuellement.

Voir le contrat d'agent → [`agents/base.py`](../../apps/jarvis-kernel/src/jarvis_kernel/agents/base.py).
