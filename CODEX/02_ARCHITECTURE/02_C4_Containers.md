# C4 — Niveau 2 : Conteneurs

`v0.2` · Statut : **En construction** · Déployable via [docker-compose](../../deploy/docker-compose.yml)

---

Les unités déployables d'HELYOS. Le **Kernel Jarvis** est la seule pièce obligatoire (local-first) ; les autres sont des **capacités optionnelles** activées au besoin.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              HELYOS (hôte local)                          │
│                                                                           │
│  ┌─────────────────────────┐         ┌──────────────────────────────┐    │
│  │   JARVIS KERNEL (API)    │◀───────▶│  Interfaces (Voice/Vision/   │    │
│  │   FastAPI · obligatoire  │  events │  Dashboard) — optionnelles   │    │
│  │   bus · gouvernance ·    │         └──────────────────────────────┘    │
│  │   mémoire · agents       │                                             │
│  └───────┬─────────┬────────┘                                             │
│          │         │                                                      │
│   state  │         │  cache/bus                                           │
│          ▼         ▼                                                      │
│  ┌────────────┐ ┌────────┐   ┌──────────┐  ┌──────────┐  ┌────────────┐  │
│  │ PostgreSQL │ │ Redis  │   │  Qdrant  │  │  Ollama  │  │   MinIO    │  │
│  │  (état,    │ │ (bus,  │   │ (mémoire │  │ (LLM     │  │ (artefacts,│  │
│  │  audit)    │ │ cache) │   │ vectoriel)│  │ locaux)  │  │  blobs)    │  │
│  └────────────┘ └────────┘   └──────────┘  └──────────┘  └────────────┘  │
│                                                                           │
│  ┌────────────────── Observabilité ───────────────────┐                  │
│  │ OpenTelemetry → Langfuse · Prometheus · Grafana · Loki │              │
│  └─────────────────────────────────────────────────────┘                 │
└─────────────────────────────────────────────────────────────────────────┘
```

## Conteneurs

| Conteneur | Rôle | Obligatoire | Tech |
|-----------|------|:-----------:|------|
| **Jarvis Kernel** | Cœur : API, bus, gouvernance, mémoire, agents | ✅ | FastAPI (Python) |
| **PostgreSQL** | État durable, journal d'audit | ⬜ (SQLite en repli) | Postgres 16 |
| **Redis** | Bus d'événements distribué, cache | ⬜ (bus mémoire en repli) | Redis 7 |
| **Qdrant** | Mémoire long terme vectorielle (RAG) | ⬜ | Qdrant |
| **Ollama** | LLM locaux | ⬜ (LiteLLM route ailleurs) | Ollama |
| **MinIO** | Stockage d'objets (artefacts, médias) | ⬜ | MinIO (S3) |
| **Observabilité** | Traces, métriques, logs | ⬜ recommandé | OTel, Langfuse, Prometheus, Grafana, Loki |
| **Interfaces** | Voice / Vision / Dashboard | ⬜ | À spécifier (RFC) |

## Principe de dégradation gracieuse

> Le Kernel démarre et passe ses tests **sans aucun service externe** (bus mémoire + store mémoire). Chaque conteneur ajouté *augmente* les capacités sans être un point de défaillance unique.

C'est l'application directe de **Local First** (ADN 2) et **Modularité absolue** (ADN 4) : on peut tout débrancher sauf le Kernel.

## Routage des LLM

Tous les appels de modèle passent par **LiteLLM** (abstraction), qui route vers Ollama (local, défaut) ou une API cloud (opt-in). Aucun composant ne connaît directement un fournisseur — principe de non-dépendance.

→ Niveau suivant : [Composants du Kernel](03_C4_Components_Kernel.md)
