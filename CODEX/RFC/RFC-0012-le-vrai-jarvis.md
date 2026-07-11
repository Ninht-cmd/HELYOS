# RFC-0012 — Le vrai Jarvis : le Pouls, la Voix, la Mémoire

- **Statut** : Accepted
- **Date** : 2026-07-07
- **Auteur** : Le Conservateur
- **Principes ADN engagés** : 3 (gouvernance), 8 (honnêteté), 14 (local d'abord)

## Le problème

« Il faut créer un vrai Jarvis du nom de HELYOS. » Un chatbot attend qu'on lui parle ;
un Jarvis **observe en continu, parle en premier, a une voix, et se souvient**. HELYOS
avait l'intelligence gouvernée (RFC-0007) mais pas ces trois organes.

## Décisions

### 1. Le Pouls (`pulse.py`) — HELYOS parle en premier

Une boucle d'observation (thread démon, intervalle `HELYOS_PULSE_INTERVAL`, 0 = coupé)
avec quatre veilleurs : validations de gouvernance en attente, tâches `[HUMAIN]`
bloquantes du portefeuille, mouvements de marché > 5 %/24 h (lecture publique,
throttlée à 10 min), connecteurs du Plan Cash débranchés. Il compose le **briefing du
Prompt Fondateur** : uniquement les décisions, anomalies, priorités — et s'il n'y a
rien : « le silence signifie que tout fonctionne. »

Invariants (testés) :
- **Le Pouls observe, il n'agit JAMAIS** — zéro écriture dans l'audit de gouvernance,
  zéro action monde.
- Un veilleur qui casse (réseau) devient une absence d'information, pas une panne.
- Les événements `pulse.*` ne partent sur le bus **qu'à la nouveauté** (pas de bruit).

Surface : `GET /pulse/briefing`, outil MCP `helyos_briefing`, briefing affiché (et dit)
au chargement de l'interface.

### 2. La Voix — synthèse et reconnaissance du navigateur

- **HELYOS parle** : `speechSynthesis` (voix française du navigateur, locale), bascule
  🔊/🔇 persistée, il se tait quand tu actives le micro.
- **HELYOS écoute** : `SpeechRecognition` (bouton 🎙). **Honnêteté affichée dans le
  pied de page** : la reconnaissance passe par le service du navigateur (Chrome envoie
  l'audio à Google) — ce n'est pas du local, et on ne prétend pas le contraire. Si le
  navigateur ne le supporte pas, le bouton disparaît au lieu de faire semblant.
- Pas de mot d'éveil (« Hey HELYOS ») en v1 : écoute permanente = micro ouvert en
  continu, refusé tant que la reconnaissance n'est pas locale (`[CHANTIER]` whisper.cpp).

### 3. La Mémoire de conversation

`jarvis.handle()` mémorise chaque échange (namespace `conversation`, plafonné à
24 entrées) ; `_talk()` réinjecte les derniers échanges dans le prompt du LLM local
(continuité) ; `GET /jarvis/history` restaure le fil au chargement — tu retrouves ta
conversation là où tu l'avais laissée, briefing frais à la suite.

## Ce que cette RFC ne prétend PAS

- Le Pouls ne « comprend » rien : ce sont des veilleurs déterministes, pas une
  conscience. La sophistication (consolidation nocturne, briefing LLM) est `[CHANTIER]` V2.
- La voix n'est pas « la voix d'HELYOS » : c'est celle du navigateur.
- La mémoire est un fil court, pas la « mémoire double » de la spec noyau (RFC-0008,
  `[CHANTIER]`).
