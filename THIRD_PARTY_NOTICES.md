# Avis tiers (Third-Party Notices)

HELYOS (cœur) est sous **AGPL-3.0**. Le **cœur n'a aucune dépendance d'exécution
obligatoire** (bibliothèque standard Python uniquement). Les composants ci-dessous sont
**optionnels** (couche serveur, observabilité, adaptateurs) ; ils restent sous leurs
licences respectives et ne sont **pas redistribués** par ce dépôt (installés par l'utilisateur).

## Dépendances optionnelles (Python)

| Composant | Usage | Licence |
|-----------|-------|---------|
| FastAPI | couche API (serveur) | MIT |
| Uvicorn | serveur ASGI | BSD-3-Clause |
| Pydantic | schémas API | MIT |
| HTTPX | client HTTP / tests API | BSD-3-Clause |
| pytest | tests (dev) | MIT |
| OpenTelemetry SDK | tracing (optionnel) | Apache-2.0 |
| LiteLLM | routage LLM (optionnel) | MIT |
| qdrant-client | mémoire vectorielle (optionnel) | Apache-2.0 |
| psycopg | adaptateur PostgreSQL (optionnel) | LGPL-3.0 |

> **Note LGPL (psycopg)** : utilisé comme bibliothèque non modifiée (liaison dynamique),
> compatible avec une distribution propriétaire des modules Pro. Ne pas *modifier* psycopg
> sans publier les modifications (LGPL).

## Services externes (non redistribués)

Le `deploy/docker-compose.yml` référence des **images publiques** exécutées comme services
séparés (PostgreSQL, Redis, Qdrant, Ollama, MinIO, Prometheus, Grafana, Loki). HELYOS ne
les redistribue pas ; chacune conserve sa propre licence.

## Texte de licence AGPL-3.0

Le fichier [`LICENSE`](LICENSE) reproduit **verbatim** le texte de la GNU AGPL-3.0
(© Free Software Foundation). La FSF autorise la copie et la distribution verbatim de ce
texte de licence — il ne s'agit donc **pas** de plagiat. Voir [CODEX/09_LEGAL](CODEX/09_LEGAL/00_Conformite_IP.md).

## Originalité du code

Le code source d'HELYOS (cœur) est **original**, écrit pour ce projet. Aucune portion de
code tiers n'y est copiée. Les frameworks ci-dessus sont **utilisés** (importés), non copiés.
