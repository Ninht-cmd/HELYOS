# Changelog HELYOS

Format inspiré de [Keep a Changelog](https://keepachangelog.com/fr/). Le Codex
versionne aussi ses décisions via [ADR](CODEX/ADR/README.md) / [RFC](CODEX/RFC/README.md).

## [0.2.0] — 2026-06-28

Première version **exécutable** : passage des documents de vision (v0.1) à un
monorepo avec un Codex structuré et un Kernel Jarvis qui démarre et se teste.

### Codex
- Codex restructuré en sections : Vision, ADN (16 principes), Architecture (C4),
  Gouvernance (A0–A5 + règles d'or), Modules, Économie, Roadmap, Tech, Glossaire.
- Process de décision : ADR (0001–0005) + RFC (0001) + gabarits.
- Modules cadrés : RuView (Wi-Fi sensing) et Cybersécurité (Blue/Red, défensif).

### Kernel Jarvis (`apps/jarvis-kernel`)
- Bus d'événements pub/sub en mémoire (ADR-0004).
- Gouvernance exécutable : `AutonomyLevel` A0–A5, `PolicyEngine`, règles d'or
  GR-1/GR-2/GR-3/GR-7 **codées et testées**, `AuditLog` immuable (ADR-0003).
- `MemoryStore` (impl en mémoire), `AgentRegistry` + `ObserverAgent` (A0).
- Observabilité : logs structurés JSON (prêts OTel/Langfuse).
- API FastAPI optionnelle : `/health`, `/agents`, `/intent`, `/governance/*`, `/events`.
- Cœur **sans dépendance** : tests via stdlib `unittest`.

### Déploiement
- `docker-compose` de l'infra locale (Postgres, Redis, Qdrant, MinIO, Ollama,
  Prometheus, Grafana, Loki) en **profils opt-in**.
- Scripts `dev.ps1` / `dev.sh`.

## [0.1.0] — antérieur

- Documents fondateurs : Vision, Mission, ADN, synthèse Codex (Foundation Pack),
  Dossier Fondateur. *(Sources préservées, voir l'historique du projet.)*
