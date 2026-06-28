# État de l'art & écosystème (Related Work)

`v0.2` · Statut : **Revue vivante** · Dernière revue : 2026-06-28

---

> Revue « niveau recherche » de ce qui existe déjà, pour situer HELYOS et préparer
> la **fusion HELYOS × Jarvis** (voir [Fusion](../02_ARCHITECTURE/05_Fusion_HELYOS_Jarvis.md)
> et [ADR-0006](../ADR/ADR-0006-fusion-jarvis-helyos-stacks.md)).
> Méthode : on cite des sources réelles ; on ne réinvente pas ce qui est mûr ; on
> n'invente de la complexité que là où aucune brique existante ne couvre le besoin (ADN 9, 11).

## ⚠️ Deux collisions de noms à connaître

| Notre terme | Projet homonyme existant | Conséquence |
|-------------|--------------------------|-------------|
| **HELYOS** | **helyOS** — framework open-source d'orchestration de véhicules autonomes (Fraunhofer IVI) | Risque de confusion **dans notre domaine même** (robotique/orchestration). À arbitrer (positionnement / nom). |
| **Jarvis** | **NVIDIA Jarvis** (renommé **Riva** en 2021) ; **Microsoft JARVIS/HuggingGPT** ; dizaines d'assistants « Jarvis » | « Jarvis » est un nom générique saturé. Le différenciateur ne sera jamais le nom, mais la **gouvernance**. |

## Cartographie comparée

### A. Orchestration de robots / flottes
- **helyOS Core** (Fraunhofer IVI) — Node.js/TypeScript, **PostgreSQL**, **RabbitMQ** (backbone d'événements), **PostGraphile** (GraphQL), un **orchestrateur d'assignations**, un **Agent SDK** (connexion des véhicules via le broker), domaines microservices. Pensé pour l'autonomie en **zones délimitées** (cours logistiques, agriculture). → Rime architecturale forte avec notre [bus d'événements](../02_ARCHITECTURE/03_C4_Components_Kernel.md) + [gouvernance](../03_GOUVERNANCE/00_Autonomie_A0_A5.md). *Ce qu'on emprunte :* le patron orchestrateur d'assignations + agents-via-broker.

### B. Perception & action incarnée (robotique « niveau PhD »)
- **NVIDIA Isaac GR00T (N1.x)** — *modèle de fondation* **vision-langage-action (VLA)** open pour humanoïdes ; **Isaac Sim/Lab** (entraînement de politiques en simulation, sim-to-real), **Isaac ROS** (middleware), **Jetson Thor** (inférence embarquée). Référence humanoïde académique annoncée à GTC Taipei (juin 2026). → Brique cible de notre module **Robotique** et d'une partie de **Vision**.
- **NVIDIA Riva** (ex-**Jarvis**) — SDK GPU de **parole** (ASR/TTS/traduction), microservices, déploiement cloud→edge→embarqué. → Brique cible de notre sous-système **Voice**.

### C. Orchestration d'agents LLM
- **NVIDIA NeMo Agent Toolkit** — bibliothèque open-source **agnostique du framework** (LangChain, LlamaIndex, CrewAI, Semantic Kernel, Google ADK), **support MCP complet** (client *et* serveur), **instrumentation/observabilité** intégrées, UI de debug. → Couche d'orchestration possible **au-dessus** de LangGraph, sans nous lier.
- **Microsoft JARVIS / HuggingGPT** (arXiv 2303.17580) — un LLM *contrôleur* pilote des modèles experts. → Fondement académique de notre principe d'**intelligence composée** (ADN 9).

### D. IA personnelle locale (la thèse la plus proche de la nôtre)
- **Stanford OpenJarvis** (Hazy Research / Scaling Intelligence Lab) — framework de recherche pour une IA personnelle **composable, on-device**. → Valide notre pari **Local First** au niveau recherche ; à suivre de près.
- Écosystème d'assistants « Jarvis » open-source (ex. *isair/jarvis* : 100 % privé, hors-ligne, mémoire SQLite, MCP). → Confirme la demande pour du **privé/local**, mais **sans gouvernance graduée** : c'est notre angle.

## Analyse de l'écart (pourquoi HELYOS existe quand même)

| Capacité | helyOS | Isaac GR00T | NeMo Toolkit | OpenJarvis | Assistants « Jarvis » | **HELYOS** |
|----------|:------:|:-----------:|:------------:|:----------:|:---------------------:|:----------:|
| Orchestration | ✅ flottes | ⬜ | ✅ agents | ◻️ | ◻️ | ✅ + gouvernée |
| Perception/action incarnée | ◻️ véhicules | ✅ VLA | ⬜ | ⬜ | ◻️ voix | 🔗 via Isaac |
| Local-first | ◻️ | ◻️ edge | ⬜ | ✅ | ✅ | ✅ |
| **Autonomie graduée A0–A5** | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ **unique** |
| **Règles d'or codées + audit** | ❌ | ❌ | ◻️ instrum. | ❌ | ❌ | ✅ **unique** |
| Codex comme source de vérité | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ **unique** |

> **Thèse de recherche (le « niveau PhD ») :** l'état de l'art sait *percevoir* (GR00T),
> *parler* (Riva), *orchestrer des agents* (NeMo) et *tourner en local* (OpenJarvis).
> Ce que **personne ne met au centre**, c'est un **kernel de gouvernance** —
> une autonomie *graduée, auditée, à veto humain architectural* — qui **enveloppe**
> ces briques. HELYOS ne réinvente pas la perception ni la parole : il invente la
> **couche de gouvernance de l'IA incarnée** et orchestre le meilleur de l'existant.

## Conséquence stratégique

1. **Ne pas reconstruire** : Voice→Riva, Robotique/Vision→Isaac GR00T, multi-agents→NeMo Toolkit/LangGraph, mémoire→Postgres/Qdrant.
2. **Construire ce qui manque** : le **kernel de gouvernance** (déjà v0), le **Codex**, l'observabilité gouvernée.
3. **Arbitrer le nom** vis-à-vis de helyOS et de la saturation « Jarvis » — voir [ADR-0006](../ADR/ADR-0006-fusion-jarvis-helyos-stacks.md) (question ouverte).

## Sources

- helyOS — [helyos_core (GitHub)](https://github.com/helyOSFramework/helyos_core) · [site](https://www.helyosframework.org/en/news.html) · [arXiv 2206.00504](https://arxiv.org/pdf/2206.00504)
- NVIDIA Jarvis→Riva — [Developer Forums](https://forums.developer.nvidia.com/t/nvidia-jarvis-has-been-renamed-to-nvidia-riva/185025) · [Riva](https://developer.nvidia.com/riva)
- NVIDIA Isaac GR00T — [Isaac GR00T](https://developer.nvidia.com/isaac/gr00t) · [Isaac-GR00T (GitHub)](https://github.com/NVIDIA/Isaac-GR00T) · [Newsroom GR00T N1](https://nvidianews.nvidia.com/news/nvidia-isaac-gr00t-n1-open-humanoid-robot-foundation-model-simulation-frameworks)
- NVIDIA NeMo Agent Toolkit — [GitHub](https://github.com/NVIDIA/NeMo-Agent-Toolkit) · [Developer](https://developer.nvidia.com/nemo-agent-toolkit)
- Microsoft JARVIS / HuggingGPT — [GitHub](https://github.com/microsoft/JARVIS) · [arXiv 2303.17580](https://arxiv.org/pdf/2303.17580)
- Stanford OpenJarvis — [GitHub](https://github.com/open-jarvis/OpenJarvis)
