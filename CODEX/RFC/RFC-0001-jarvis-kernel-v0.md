# RFC-0001 — Périmètre du Kernel Jarvis v0

- **Statut** : Accepted
- **Date** : 2026-06-28
- **Auteur** : Le Conservateur
- **Principes ADN engagés** : 4, 6, 9, 11, 16

## Résumé

Définir le **périmètre minimal** d'un Kernel Jarvis **réellement exécutable**, qui matérialise les principes du Codex sans sur-ingénierie (ADN 11).

## Problème / friction

Le projet existait sous forme de **documents de vision** uniquement (v0.1). Friction : impossible de *construire* ou de *vérifier* quoi que ce soit. Il faut un socle de code qui démarre, se teste, et incarne la gouvernance — le pont entre vision et système.

## Proposition

Un Kernel v0 (`apps/jarvis-kernel`) contenant **exactement** :

1. **EventBus** (pub/sub en mémoire) — colonne vertébrale (ADR-0004).
2. **Gouvernance** — `AutonomyLevel` (A0–A5), `PolicyEngine` (ALLOW/REQUIRE_VALIDATION/DENY), règles d'or, `AuditLog` (ADR-0003).
3. **MemoryStore** — interface + impl mémoire.
4. **Agent / AgentRegistry** — contrat d'agent déclarant son niveau requis.
5. **API FastAPI** — `/health`, `/agents`, `/intent` (soumettre une intention, voir la décision de gouvernance).
6. **Observabilité** — logs structurés, hooks OTel.

**Hors périmètre v0** (volontairement) : Voice, Vision, Robotics, persistance réelle, LangGraph, RAG. Ils viendront par RFC dédiées (ADN 11 : complexité maîtrisée).

## Gouvernance

Le Kernel **est** le lieu de la gouvernance. L'endpoint `/intent` démontre le flux complet : une intention est évaluée, classée (niveau requis + règles d'or), et renvoie une décision **tracée**.

## Local-first & réversibilité

Zéro service externe requis : bus mémoire + store mémoire. `docker-compose` fournit l'infra complète en **opt-in**. Chaque composant est derrière une interface → substituable.

## Observabilité

- `/health` expose l'état.
- Chaque décision de gouvernance est journalisée et **interrogeable**.
- Logs structurés prêts pour OpenTelemetry.

## Alternatives

- *Commencer par les interfaces (Voice/Vision)* — rejeté : sans cœur gouverné, on construirait sur du sable.
- *Framework d'agents lourd dès v0* — rejeté (ADN 11).

## Questions ouvertes

- Format exact des événements (schéma versionné ?) → RFC future.
- Persistance de l'AuditLog (fichier → Postgres) → Alpha.
