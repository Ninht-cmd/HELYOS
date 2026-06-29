# RFC-0004 — Orchestration d'agents composés (sous gouvernance)

- **Statut** : Accepted
- **Date** : 2026-06-29
- **Auteur** : Le Conservateur
- **Principes ADN engagés** : 4, 6, 9, 11

## Résumé

Un mécanisme léger pour **composer plusieurs agents** (intelligence composée, ADN 9),
chaque étape passant par la gouvernance, et **compatible** avec LangGraph / NeMo Agent
Toolkit sans s'y lier (ADN 4, 11).

## Problème / friction

Un agent seul est limité. La valeur naît de la **composition** (analyser → décider →
agir → tracer). Mais composer des agents qui *agissent* sans cadre serait dangereux :
il faut que **chaque étape reste gouvernée et auditée**.

## Proposition

- `LLMPort` (abstraction modèle) + `StubLLM` (déterministe local) ; adaptateurs LiteLLM/NeMo plus tard.
- `ResearchAgent` (A1) : analyse via `LLMPort`, range la trouvaille en mémoire.
- `Orchestrator.run(steps, granted)` : exécute une séquence `Step(agent, context)` ;
  **chaque étape → gouvernance** ; **arrêt sûr** dès qu'une étape n'est pas `ALLOW`.
- Trace complète (`StepResult`) + événements `orchestrator.completed|halted`.

## Gouvernance

Aucune dérogation : l'orchestrateur ne fait qu'**enchaîner** des soumissions à la
gouvernance. Une étape A2 non accordée **suspend** la chaîne (pas d'exécution furtive).

## Local-first & réversibilité

`StubLLM` rend l'orchestration testable hors-ligne. L'`Orchestrator` est remplaçable par
un graphe LangGraph ou une intégration NeMo derrière le même contrat.

## Observabilité

Spans `orchestrator.run` / `research.analyze` ; événements bus ; entrées d'audit par étape.

## Alternatives

- *Adopter LangGraph/NeMo directement dès maintenant* — rejeté en v0.3 (ADN 11 : on pose
  d'abord le contrat gouverné minimal ; on enveloppe les frameworks ensuite).

## Questions ouvertes

- Graphes (branches, boucles) au-delà de la séquence ? → quand LangGraph sera intégré.
- Politique de reprise après une étape `REQUIRE_VALIDATION` validée par le Conservateur.
