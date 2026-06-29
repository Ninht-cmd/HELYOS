# Changelog HELYOS

Format inspiré de [Keep a Changelog](https://keepachangelog.com/fr/). Le Codex
versionne aussi ses décisions via [ADR](CODEX/ADR/README.md) / [RFC](CODEX/RFC/README.md).

## [0.3.1] — 2026-06-29 — Modèle économique & licence

### Stratégie / Codex
- **Licence : AGPL-3.0** pour le cœur ouvert + **dual-licensing** commercial — [ADR-0005](CODEX/ADR/ADR-0005-licence.md) `Accepted`.
  Fichier [`LICENSE`](LICENSE) ajouté (texte AGPL-3.0 verbatim). Résout le dépôt public « tous droits réservés ».
- **Modèle Open Core** — [ADR-0008](CODEX/ADR/ADR-0008-open-core-business-model.md) `Accepted`.
- Section Économie développée : [business model](CODEX/05_ECONOMIE/01_Business_Model.md) (paliers, chemin vers
  ~100 k€/mois, wedge « IA gouvernée pour secteurs régulés ») + [frontière open/Pro](CODEX/05_ECONOMIE/02_Frontiere_Open_Core.md).
- Orchestration d'agents : [RFC-0004](CODEX/RFC/RFC-0004-orchestration-agents.md) ; arbitrage du nom : [RFC-0003](CODEX/RFC/RFC-0003-arbitrage-du-nom.md).
- Dépôt publié : https://github.com/Ninht-cmd/HELYOS

## [0.3.0] — 2026-06-29 — Fondations Alpha

Entrée dans le jalon **Alpha** : mémoire persistante, observabilité, premier agent,
et alignement stratégique sur l'écosystème (revue de l'existant + fusion HELYOS × Jarvis).

### Codex
- Section **08_ECOSYSTEME** : [état de l'art](CODEX/08_ECOSYSTEME/00_Etat_de_lart.md) (helyOS/Fraunhofer,
  NVIDIA Isaac GR00T, Riva ex-Jarvis, NeMo Agent Toolkit, Stanford OpenJarvis) avec sources.
- **Fusion HELYOS × Jarvis** ([thèse](CODEX/02_ARCHITECTURE/05_Fusion_HELYOS_Jarvis.md)) : Jarvis devient
  la couche d'incarnation gouvernée ; contribution « Governed Embodiment ».
- [ADR-0006](CODEX/ADR/ADR-0006-fusion-jarvis-helyos-stacks.md) (fusion & stacks externes) ·
  [ADR-0007](CODEX/ADR/ADR-0007-fondations-alpha-memoire-observabilite-scribe.md) (*écrit par le ScribeAgent*) ·
  [RFC-0002](CODEX/RFC/RFC-0002-scribe-agent.md) (ScribeAgent).

### Kernel — fondations Alpha (1+2+3)
- **(1) Mémoire persistante** derrière `MemoryStore` : `SqliteMemoryStore` (local, défaut persistant),
  adaptateurs `PostgresMemoryStore` et `QdrantVectorMemory` (optionnels), `NaiveVectorMemory`
  (recherche sémantique locale de repli). Fabrique `build_memory(backend)`.
- **(2) Observabilité** : `setup_tracing` / `span` — OpenTelemetry → OTLP/Langfuse, optionnel et
  no-op si absent ; flux de gouvernance instrumenté.
- **(3) ScribeAgent** (A2) : transforme une décision en ADR via la gouvernance ; indexe le Codex
  en mémoire. Démo end-to-end : 33 docs indexés, ADR-0007 écrit sous gouvernance.
- Suite de tests : **47 verts** (dont persistance SQLite, vectoriel, Scribe A1/A2).

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
