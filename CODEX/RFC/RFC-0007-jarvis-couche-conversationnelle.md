# RFC-0007 — Jarvis : la couche conversationnelle unifiée (et son interface honnête)

- **Statut** : Accepted
- **Date** : 2026-07-06
- **Auteur** : Le Conservateur
- **Principes ADN engagés** : 3 (gouvernance), 8 (honnêteté), 11 (un pas à la fois), 14 (local d'abord)

## Résumé

On ne parle plus à cinq agents épars : on parle à **une seule intelligence**. `jarvis.py` reçoit
du langage naturel, classe l'intention, route vers la capacité déjà construite (portefeuille,
factures, business, recherche), **agit sous gouvernance A0–A5** et répond — le refus faisant
partie de la réponse. Exposé par `POST /jarvis` (API), `python -m jarvis_kernel.chat` (REPL)
et l'interface web `/app/`.

## Problème / friction

Le kernel avait des capacités réelles et testées, mais **aucun point d'entrée unifié** : l'agent
de factures, le portefeuille et la gouvernance vivaient chacun derrière leur propre API. Ce
n'est ni le « moment Jarvis » de la vision, ni utilisable par un non-développeur. L'interface
web existante était l'inverse : un décor 3D sans cerveau, avec des métriques inventées
(« Objectifs : 82 % ») — exactement le vaporware que le Codex interdit.

## Proposition

**Compréhension** (`classify`) : règles déterministes d'abord (testables, zéro réseau, les
actions dangereuses testées EN PREMIER), LLM local en départage des cas ambigus. Une réponse
LLM n'est acceptée que si elle est courte et exactement une étiquette — un écho de prompt est
rejeté.

**Action** : chaque intention appelle l'agent déjà testé. Toute action risquée est **soumise**
au `PolicyEngine` ; le verdict (`allow` / `require_validation` / `deny` + règle d'or) est rendu
à l'utilisateur, dans le texte ET dans les données de la réponse.

**Interface** (`web/`) : conversationnelle, branchée sur `POST /jarvis`. Contrat d'honnêteté :
- les panneaux (« Agents », « Audit », « Flux du noyau », « Portefeuille ») affichent
  **exclusivement l'état réel du serveur** (`/agents`, `/governance/audit`, `/events`,
  `/portfolio`) — états vides affichés comme tels, aucune métrique inventée ;
- le verdict de gouvernance est un **élément d'interface de première classe** (badge
  vert/ambre/rouge + règle d'or) ;
- la 3D est une ambiance optionnelle (l'UI fonctionne sans WebGL) et ne chevauche jamais le
  contenu ;
- accessibilité : focus visible, `aria-live` sur le fil, `prefers-reduced-motion` respecté.

## Gouvernance & honnêteté

- Jarvis n'ajoute **aucun pouvoir** : il route vers des agents dont les niveaux (A0–A5) et les
  règles d'or s'appliquent inchangés. GR-1/GR-2/GR-3/GR-7 vérifiées de bout en bout par tests.
- La classification par règles est volontairement conservatrice : « supprime mes factures »
  déclenche la gouvernance, pas la rédaction de relances.
- Sans Ollama, le repli est **annoncé** à l'utilisateur (pas de fausse conversation).

## Alternatives rejetées

- *Un framework d'orchestration externe (LangGraph, n8n)* — recoderait par l'infra ce que le
  kernel fait déjà, pour zéro capacité nouvelle (ADR-0010, « ne jamais recoder ce qui existe »).
- *Garder une UI par agent* — c'est l'anti-Jarvis : la valeur est l'unification.
- *Une UI « cinématique » d'abord* — rejetée par le fondateur puis par les faits : un décor
  sans cerveau est du vaporware. Le cerveau d'abord, l'interface le sert.
