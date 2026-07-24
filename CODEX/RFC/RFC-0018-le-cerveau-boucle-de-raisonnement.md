# RFC-0018 — Le cerveau : la boucle de raisonnement (l'IA, pas la coquille)

- **Statut** : Accepted
- **Date** : 2026-07-24
- **Auteur** : Le Conservateur (« crée l'IA, pas une coquille vide »)

## Le problème, nommé en ingénieur

Jusqu'ici HELYOS était un **menu** : intention → handler → réponse, en un tour.
Ça ressemble à une coquille parce que ça n'en est presque une : aucun raisonnement
multi-étapes, aucun choix autonome d'outils. La différence entre une coquille et
une IA n'est pas le nombre de features — c'est la **boucle d'agent** : recevoir un
objectif, décider quels outils lire, les enchaîner, observer, et synthétiser.

## Décision

`agents/reasoning.py` — un agent **ReAct** qui tourne sur le simple `/api/generate`
de qwen3:14b (pas besoin de l'API tool-calling native, donc robuste et testable) :

1. Objectif → le LLM émet **une action JSON** `{"outil","args"}`.
2. HELYOS exécute l'outil (lecture gouvernée A1), rend le résultat au LLM.
3. Le LLM recommence, jusqu'à `{"final": ...}` ou la limite d'étapes.

Six outils de LECTURE : portefeuille, tresorerie, prospection, commandes, marche,
bibliotheque. Cache anti-répétition (rappeler le même outil ne le ré-exécute pas
→ efficacité, moins d'appels). Synthèse finale ancrée si la limite est atteinte.

## La frontière, non négociable

**Les outils du cerveau sont TOUS en lecture.** Le cerveau observe, croise,
raisonne et **propose** — il ne dépense, ne signe, ne supprime jamais seul.
GR-2/GR-7 restent la limite : une action sur le monde passe toujours par la
validation humaine. Une IA qui agit sur l'irréversible sans toi n'est pas un
Jarvis, c'est un incident en attente. La puissance de raisonnement **augmente**
l'exigence de gouvernance, elle ne la contourne pas.

## Preuve (mesurée, en réel)

Objectif donné à qwen3:14b : « croise ma trésorerie, mon portefeuille et mes
prospects, donne LA priorité ». L'IA a **choisi elle-même** d'appeler
`portefeuille` puis `tresorerie`, a lu l'état RÉEL, et a conclu :
> « Trésorerie 0€. Portefeuille : 8 projets, 3 bloqués (Printful, paiement).
> Priorité : débloquer Printful et paiement pour Atelier Compagnon. »

Aucun chiffre inventé — tout vient des observations. C'est de l'intelligence
appliquée à ta réalité, pas une coquille.

## Surface

Chat : « que dois-je faire », « analyse ma situation », « ma priorité »,
« objectif : … ». API : `POST /agent/run {goal}`. 6 tests hermétiques (LLM
scripté) prouvent la boucle sans réseau.

## Suite possible

Donner au cerveau les **outils MCP** (ADR-0012) comme outils de lecture
supplémentaires → il raisonne sur tout l'écosystème branché. Et, un jour, sous
validation stricte, des outils d'ACTION (rédiger une relance, préparer une
commande) — mais toujours derrière GR-2, jamais en autonomie sur l'argent.
