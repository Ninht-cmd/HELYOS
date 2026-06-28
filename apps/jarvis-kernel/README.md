# Jarvis Kernel

> Le cœur gouverné d'HELYOS. `Jarvis = Kernel + Mémoire + Agents + Outils + Gouvernance + Observabilité.`

Implémente le périmètre de [RFC-0001](../../CODEX/RFC/RFC-0001-jarvis-kernel-v0.md). **Le cœur ne dépend que de la bibliothèque standard** : il démarre et se teste sans aucun service externe (Local First, [ADN 2](../../CODEX/01_ADN/00_ADN.md)).

## Démarrage

```bash
# Tests du cœur — ZÉRO dépendance (juste Python ≥ 3.11)
python -m unittest discover -s tests -t . -v
#   (depuis ce dossier, avec src sur le PYTHONPATH — voir scripts/dev.ps1)

# Couche serveur (API HTTP) — optionnelle
pip install -e ".[server]"
python -m jarvis_kernel              # → http://127.0.0.1:8080
#   docs interactives : http://127.0.0.1:8080/docs
```

## Architecture interne

Voir le [C4 niveau 3](../../CODEX/02_ARCHITECTURE/03_C4_Components_Kernel.md). En bref :

```
src/jarvis_kernel/
├─ kernel/event_bus.py        # Bus pub/sub (colonne vertébrale, ADR-0004)
├─ governance/
│  ├─ autonomy.py             # AutonomyLevel A0–A5
│  ├─ policy.py               # PolicyEngine + règles d'or (GR-1…GR-7)
│  ├─ audit.py                # Journal d'audit immuable
│  └─ service.py              # Évalue → journalise → publie (instrumenté OTel)
├─ memory/
│  ├─ store.py                # MemoryStore (interface) + InMemory
│  ├─ sqlite_store.py         # ✦ Persistant local (défaut hors tests)
│  ├─ postgres_store.py       # ✦ Adaptateur Postgres (optionnel)
│  ├─ vector.py               # ✦ NaiveVectorMemory (local) + Qdrant (optionnel)
│  └─ __init__.py             # build_memory(backend)
├─ agents/
│  ├─ base.py                 # Agent + AgentRegistry (+ ObserverAgent A0)
│  └─ scribe.py               # ✦ ScribeAgent (A2) — rédige des ADR (RFC-0002)
├─ observability/
│  ├─ telemetry.py            # Logs structurés JSON
│  └─ tracing.py              # ✦ OpenTelemetry → OTLP/Langfuse (no-op si absent)
├─ api/                       # Couche FastAPI (optionnelle)
├─ context.py                 # Câblage partagé des composants
├─ config.py                  # Settings (env, stdlib)
└─ main.py                    # create_app() — application ASGI
```

> ✦ = ajouts **Alpha (v0.3)** : mémoire persistante, observabilité, premier agent.

### Configuration (variables d'env)

| Variable | Défaut | Rôle |
|----------|--------|------|
| `HELYOS_MEMORY_BACKEND` | `memory` | `memory` \| `sqlite` (persistant) \| `postgres` |
| `HELYOS_MEMORY_PATH` | `helyos_memory.sqlite` | Chemin SQLite |
| `HELYOS_OTEL_ENABLED` | `0` | `1` pour activer le tracing |
| `HELYOS_OTEL_ENDPOINT` | `http://localhost:4318` | Collecteur OTLP / Langfuse |
| `HELYOS_DEFAULT_AUTONOMY` | `A1` | Niveau accordé par défaut |

## Le flux d'une intention

Toute action passe par la gouvernance avant exécution ([ADR-0003](../../CODEX/ADR/ADR-0003-governance-kernel.md)) :

```
POST /intent {action_type, granted_level, has_backup, sensitive, validated, …}
        │
        ▼
  PolicyEngine.evaluate() → ALLOW | REQUIRE_VALIDATION | DENY
        │
        ├─ AuditLog.append()   (toujours tracé — ADN 16)
        └─ EventBus.emit()     (governance.decided + action.*)
```

### Exemples (cURL)

```bash
# Lecture en A0 → ALLOW
curl -s -X POST localhost:8080/intent -H "content-type: application/json" \
  -d '{"action_type":"read","granted_level":"A0"}'

# Suppression sans sauvegarde, même en A5 → DENY (GR-1)
curl -s -X POST localhost:8080/intent -H "content-type: application/json" \
  -d '{"action_type":"delete","granted_level":"A5","has_backup":false}'

# Transaction financière, même en A5 → REQUIRE_VALIDATION (GR-7)
curl -s -X POST localhost:8080/intent -H "content-type: application/json" \
  -d '{"action_type":"financial","granted_level":"A5"}'
```

## Tests

La suite couvre l'échelle A0–A5, **chaque règle d'or** (GR-1, GR-2, GR-3, GR-7), le bus, la mémoire, le service, et l'API (ignorée si FastAPI absent). Les tests de gouvernance sont le **miroir exécutable** du Codex : ils échouent si le code et le Codex divergent.
