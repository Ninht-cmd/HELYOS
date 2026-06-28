# Stack technique de référence

`v0.2` · Statut : **Stable (révisé par ADR)** · *API cloud : uniquement si nécessaire.*

---

La stack matérialise l'ADN : **open-source d'abord** (3), **local d'abord** (2), **non-dépendance** (tout est derrière une abstraction). Aucune brique n'est un point de dépendance unique.

## Par couche

| Couche | Brique | Rôle | Principe |
|--------|--------|------|----------|
| **API / Cœur** | **FastAPI** | Surface HTTP du Kernel | Léger, typé, async |
| **Conteneurisation** | **Docker** | Packaging, reproductibilité | Réversibilité |
| **État** | **PostgreSQL** | Données durables, audit | Standard, durable |
| **Cache / Bus** | **Redis** | Bus distribué, cache, files | Découplage |
| **Mémoire vectorielle** | **Qdrant** | RAG, mémoire long terme | Local, open-source |
| **LLM local** | **Ollama** | Modèles locaux par défaut | Local First (2) |
| **Routage LLM** | **LiteLLM** | Abstraction multi-fournisseurs | Non-dépendance |
| **Orchestration agents** | **LangGraph** | Graphes d'agents, états | Intelligence composée (9) |
| **RAG / Index** | **LlamaIndex**, **Haystack** | Ingestion, retrieval | Modularité |
| **Traces** | **OpenTelemetry** | Instrumentation standard | Observable (6) |
| **LLM Observability** | **Langfuse** | Traçage des appels LLM | Observable (6) |
| **Métriques** | **Prometheus** + **Grafana** | Mesure, dashboards | Mesurable (8) |
| **Logs** | **Loki** | Agrégation de logs | Observable (6) |
| **Objets / Blobs** | **MinIO** | Artefacts, médias (S3) | Local, S3-compatible |
| **Automatisation web** | **Playwright** | Action navigateur, lecture d'écran | Action gouvernée |
| **Vision** | **MediaPipe** | Perception visuelle | Modulaire |
| **Interop outils** | **MCP** | Connecteurs standardisés | Composition |

## Règles d'évolution de la stack

1. **Toute nouvelle dépendance = un ADR.** On justifie le besoin, l'alternative open-source, et le chemin de sortie.
2. **Pas de couplage direct à un fournisseur.** Un LLM ⇒ derrière LiteLLM. Une base ⇒ derrière une interface (`MemoryStore`, repository).
3. **Le Kernel tourne sans la stack lourde.** En dev/test : bus mémoire + store mémoire, **zéro conteneur requis** (voir [docker-compose](../../deploy/docker-compose.yml) pour le mode complet).
4. **API cloud = opt-in justifié.** Jamais requise pour le cœur (ADN 2).

## État d'implémentation (v0.2)

- ✅ **FastAPI** — Kernel API.
- ✅ **Bus mémoire** (abstraction prête pour Redis).
- ✅ **MemoryStore mémoire** (abstraction prête pour Postgres/Qdrant).
- ✅ **Logs structurés** (abstraction prête pour OTel/Loki).
- 🔧 **Docker-compose** — infra locale fournie, à brancher en Alpha.
- ⬜ Le reste — câblé au fil de la [roadmap](../06_ROADMAP/00_Roadmap.md).

> Voir les décisions : [ADR](../ADR/README.md).
