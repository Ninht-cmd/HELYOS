# ADR-0011 — STARK est le corps, HELYOS est le cerveau gouverné

- **Statut** : Accepted
- **Date** : 2026-07-16
- **Décideur** : Le Conservateur
- **Contexte** : deux projets sur le Bureau — `HELYOS` (kernel gouverné, 191 tests)
  et `STARK` (shell Tauri « Iron Man » : orchestrateur + HUD + modules JARVIS/
  ULTRON/EDITH, ~600 lignes, surtout du scaffold). Le module JARVIS de STARK
  renvoyait un stub (« [stub] reçu … ») avec un TODO « brancher le vrai agent
  registry ». Demande du fondateur : « lie STARK et HELYOS en améliorant ».

## Décision

**On superpose, on ne fusionne pas.** Fusionner deux bases (l'une testée, l'autre
scaffold) ne produirait qu'une base moins testée. À la place :

- **STARK = le corps.** Shell Tauri (Rust), HUD React, bus d'événements WebSocket,
  ULTRON (automatisation), EDITH (sécurité/sentinelle). Toute la couche « cinéma »
  et système.
- **HELYOS = le cerveau gouverné.** Cognition, agents, gestion de business (caisse,
  prospection, portefeuille), et surtout la **gouvernance A0–A5** (règles d'or).
- **Le pont** : le module `JarvisModule` de STARK délègue chaque `/ask` à
  `HELYOS POST /jarvis` (stdlib `urllib`, appel dans un thread, `HELYOS_URL`
  configurable). Le verdict de gouvernance est republié sur le bus STARK
  (`governance.decision`, `jarvis.response`) → le HUD et EDITH le voient en direct.

## Conséquences

- **Tout ce que STARK fait via JARVIS est gouverné.** Vérifié de bout en bout :
  « supprime tout » → `deny` GR-1 ; « fais un virement » → `require_validation`
  GR-7 ; une question normale passe. La gouvernance n'est pas dupliquée dans STARK :
  elle vit à un seul endroit (HELYOS), testée à un seul endroit.
- **Honnêteté de dégradation** : si HELYOS est éteint, JARVIS le DIT et n'invente
  aucune réponse (`status: degraded`, event `jarvis.degraded`). Un corps sans
  cerveau ne fait pas semblant de penser.
- **Frontière nette pour l'avenir** : ULTRON (automatisation) et EDITH (sécurité)
  pourront eux aussi soumettre leurs actions à HELYOS quand ils deviendront réels —
  même porte, même gouvernance. STARK n'aura jamais sa propre gouvernance parallèle.

## Alternatives rejetées

- **Fusionner STARK dans HELYOS** : perte du shell Tauri/HUD déjà en place, et
  mélange Rust/desktop dans un kernel qui doit rester local-first et testable.
- **Recoder la cognition dans STARK** : c'est refaire HELYOS en moins bien, sans
  ses 191 tests ni sa gouvernance. Le stub restait un stub.
- **Dupliquer la gouvernance côté STARK** : deux sources de vérité = deux failles.
  La règle d'or vit dans le kernel, point.

## Fichiers touchés (repo STARK, non versionné à ce jour)

`modules/jarvis/python/jarvis/module.py` (pont), `modules/stark/python/stark/config.py`
(`helyos_url`), `.env.example`, `README.md`. À versionner : `git init` sur STARK
recommandé (voir [[helyos-project]] pour la stratégie mono/multi-repo).
