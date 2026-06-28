# Fusion HELYOS × Jarvis — thèse d'architecture

`v0.2` · Statut : **Proposé (cadre la suite)** · Décision : [ADR-0006](../ADR/ADR-0006-fusion-jarvis-helyos-stacks.md)

---

## Le changement de cadre

Jusqu'ici : *« Jarvis est un produit d'HELYOS. »* La fusion pousse l'idée plus loin :

> **Jarvis n'est pas un produit à côté du kernel — c'est la couche d'incarnation
> (perception, parole, action, robotique) que le kernel HELYOS *gouverne*.**
> HELYOS = le **cerveau gouverné** ; Jarvis = le **corps**. Un seul organisme.

Ce n'est pas une fusion de marques, c'est une **fusion architecturale** : tout ce qui
perçoit, parle ou agit (Jarvis) passe sous l'autorité de la gouvernance A0–A5 et du
Codex (HELYOS). Aucune capacité incarnée n'échappe au kernel.

## La contribution originale (le « niveau PhD »)

L'état de l'art ([Related Work](../08_ECOSYSTEME/00_Etat_de_lart.md)) sait percevoir, parler,
orchestrer et tourner en local. La **brique manquante** que HELYOS apporte :

> **« Governed Embodiment »** — une couche de **gouvernance graduée, auditée et à veto
> humain architectural**, qui enveloppe des modèles de fondation incarnés (VLA),
> de la parole temps réel et des flottes d'agents, sans dépendre d'un fournisseur unique.

Énoncé de thèse :
> *Comment garantir qu'un système d'IA incarné, composé de modèles hétérogènes et
> capables d'agir sur le monde physique, reste en permanence compréhensible,
> auditable et interruptible — sans sacrifier la capacité d'action ?*
> **Réponse HELYOS :** un kernel de gouvernance (A0–A5 + règles d'or) placé sur le
> chemin critique de toute action, de l'octet logiciel à l'actionneur physique.

## Mapping : sous-système Jarvis → meilleur stack existant

| Sous-système Jarvis | Brique externe adoptée | Rôle de HELYOS (la valeur ajoutée) |
|---------------------|------------------------|-------------------------------------|
| **Voice** | **NVIDIA Riva** (ex-Jarvis) — ASR/TTS/NMT | Gouverner *ce que* la voix déclenche (une commande vocale = une intention soumise à A0–A5). |
| **Vision** | **Isaac** (perception) + MediaPipe | Classer les actions issues de la vision ; garde-fous (ex. RuView). |
| **Robotics** | **Isaac GR00T** (VLA), Isaac Sim/Lab/ROS, **Jetson Thor** | L'étape *Act* physique passe par la gouvernance (action physique = A2+). |
| **Agents (Business/Research)** | **NeMo Agent Toolkit** + **LangGraph**, **MCP** | Registre + niveaux requis par agent ; audit ; veto. |
| **Memory** | **PostgreSQL** + **Qdrant** (RAG) | Mémoire souveraine, locale, derrière `MemoryStore`. |
| **Kernel** | *(propre à HELYOS)* | Bus, **gouvernance**, audit, observabilité. **Non délégable.** |

> Principe de non-dépendance (ADN) : chaque brique externe est derrière une **interface**
> (LiteLLM pour les LLM, `MemoryStore` pour la mémoire, un futur `ActuatorPort` pour Isaac).
> On adopte sans se lier.

## Architecture cible (incarnation gouvernée)

```
            ┌─────────────────────── HELYOS (cerveau gouverné) ───────────────────────┐
            │   Codex (vérité)   ·   EventBus   ·   Gouvernance A0–A5 + règles d'or    │
            │                         ·   Audit   ·   Observabilité (OTel)            │
            └───────▲───────────────────────┬───────────────────────────────▲────────┘
        intentions  │ (toute action gouvernée : du logiciel à l'actionneur)  │ traces
            ┌───────┴───────┐   ┌───────────┴───────────┐   ┌───────────────┴────────┐
            │     VOICE      │   │   AGENTS (composés)   │   │   ROBOTICS / VISION     │
            │  NVIDIA Riva   │   │ NeMo Toolkit+LangGraph│   │  Isaac GR00T (VLA)      │
            │  (ASR/TTS)     │   │  + MCP + LiteLLM      │   │  Isaac Sim/ROS · Jetson │
            └───────────────┘   └───────────────────────┘   └─────────────────────────┘
                    └─────────────── Jarvis = le corps incarné ───────────────┘
```

La **boucle OODA** ([Jarvis](04_Jarvis.md)) devient physique : *Observe* (Riva/Isaac/RuView)
→ *Orient* (mémoire + RAG) → *Decide* (agents NeMo/LangGraph) → ***Act* (gouverné A0–A5)**.

## Inspiration d'orchestration : helyOS (Fraunhofer)

Le projet homonyme **helyOS** (orchestrateur d'assignations pour flottes, RabbitMQ +
Postgres + Agent SDK) est un **patron de référence** pour notre couche flotte/edge :
*assignations → agents via broker → suivi temps réel*. On s'en inspire pour le module
**Robotique**, **sans** en dépendre, et en **traçant la collision de nom** (ADR-0006).

## Feuille de route de la fusion (incréments gouvernés)

1. **Ports d'incarnation** : définir les interfaces `VoicePort`, `ActuatorPort`, `PerceptionPort` (RFC) — la gouvernance s'y insère.
2. **Voice (Riva)** : une commande vocale → `Intent` → gouvernance → action. POC A1/A2.
3. **Agents (NeMo/LangGraph)** : orchestrer ≥ 2 agents sous registre + niveaux requis.
4. **Robotique (Isaac, simulation d'abord)** : *Act* physique en **simulation** (Isaac Sim), action physique réelle = **A2 minimum** + règles d'or.
5. **Arbitrage du nom** (ADR-0006) : résoudre HELYOS vs helyOS et la saturation « Jarvis ».

> Règle d'or de la fusion : **aucune capacité incarnée n'est intégrée sans passer par
> la gouvernance et sans test.** Le corps obéit toujours au cerveau gouverné.
