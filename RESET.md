# HELYOS — Reset honnête (v2)

> Issu d'une analyse multi-agents (inventaire du code réel → 4 architectures → gate anti-vaporware → synthèse).
> Règle : aucun composant sans algorithme / entrées / sorties / **métrique**. Le langage décoratif (« cortex »,
> « incarnation Jarvis ») est retiré : non mesurable.

## Ce qu'HELYOS EST (une phrase, vérifiable)

Un **point de contrôle gouverné, mesurable et audité** inséré entre une *intention* (proposée par un agent) et
son *exécution* : la chaîne `submit() → PolicyEngine A0–A5 + règles d'or → AuditLog`. Blocage des actions
nuisibles **chiffré** : `block_rate = 1.0` sur 42 scénarios honnêtes, **0 fuite**, baseline non-gouvernée `0.0`.
Verrouillé par **72 tests**.

## Ce qu'HELYOS N'EST PAS (honnêteté)

1. **Pas des « agents intelligents »** — hors `ResearchAgent`+Ollama, les agents sont des `StubLLM` déterministes (aucune cognition). On garde le *contrat* d'agent (prouvé), on jette l'affirmation d'autonomie cognitive.
2. **Pas une gouvernance qui protège d'un agent malveillant** — la v0 juge la *déclaration*, pas la réalité : **6/6 contournements adverses réussissent** (prouvé et documenté).
3. **Pas une « mémoire sémantique / RAG »** — `NaiveVectorMemory` = sac-de-mots lexical ; `QdrantVectorMemory` lève `NotImplementedError`.
4. **Pas une plateforme qui EXÉCUTE et observe ses effets** — **aucun effecteur n'existe** ; `action.executed` n'apparaît que dans un docstring. Donc toute « boucle de réconciliation / Digital Twin / sandbox » présuppose une couche d'exécution **absente**.
5. **Pas une « incarnation Jarvis »** — le dashboard est cosmétique, sans métrique.

## Gardé (prouvé, avec preuve)

`governance/` (policy+autonomy, couverture 100%) · `eval/governance_bench.py` (banc falsifiable qui expose sa
propre faille) · `kernel/event_bus.py` (93%) · `agents/base+orchestrator` (composition gouvernée testée) ·
`agents/scribe.py` (95%) · `service+audit` (journal immuable) · `licensing/license.py` (HMAC, 98% — **réutilisable
comme primitive de preuve**) · `memory/store+sqlite` (97/100%) · `observability/telemetry` · `OllamaLLM`+`llm_bench`
(**reclassé « mesuré une fois », pas « prouvé »**).

## Jeté (illusions / promesses)

La promesse que la gouvernance v0 protège du mensonge · l'« intelligence » des agents stub · le « RAG sémantique
fonctionnel » · le dashboard comme capacité · le label « proven » sur OllamaLLM · les composants (Digital Twin,
sandbox) présentés comme *réutilisant l'existant* alors qu'ils reposent sur un effecteur inexistant · le slogan
« ça referme LE trou » (battre 6 attaques figées écrites dans le vocabulaire du classifieur est quasi-tautologique).

## Questions de recherche (falsifiables)

1. Un **ReclassifierGate lexical** fait-il passer l'adversarial de 0/6 à ≥5/6 **sans** un seul faux positif sur un jeu honnête ÉLARGI d'actions légitimes *porteuses du lexique* ? *(Le fp=0.0 actuel est vacant : les scénarios ont un texte vide.)*
2. Robustesse à un **adversaire adaptatif** (paraphrase/unicode) ?
3. Un **FlagVerifier crypto** (sha256 du backup, jeton HMAC lié au hash d'action) ferme-t-il 100% de `ment_backup`/`ment_validation` **et** résiste-t-il au rejeu ?
4. Une **couche d'exécution confinée** (sous-processus à privilège minimal, réseau coupé) atteint-elle `containment_rate = 1.0` ? *(Prérequis honnête : cet effecteur n'existe pas ; l'in-process n'offre aucune garantie.)*

## Roadmap (chaque phase = un benchmark de sortie)

| Phase | Objectif | Benchmark de sortie |
|---|---|---|
| **0 — Honnêteté du banc** | Rendre la garde discriminante | ≥15 actions honnêtes *porteuses du lexique* ajoutées ; honest `block_rate=1.0`, `fp=0.0` sur ≥57 scénarios |
| **1 — FlagVerifier** | Fermer `ment_backup`/`ment_validation` par la **vérité** crypto (réutilise `license.py`) | ces 2 : 0/2 → 2/2 ; rejeu rejeté 100% ; faux rejet 0% ; honnêtes ne régressent pas |
| **2 — ReclassifierGate** | Fermer les 4 sous-déclarations de type | adversarial global 0/6 → 6/6 ; `fp=0.0` ; latence p95 même ordre |
| **3 — Paraphrase (recherche)** | Le lexique tient-il ? | ≥30 variantes paraphrasées ; ≥0.8 = ok, sinon embedder documenté |
| **4 — Exécution confinée (recherche/build)** | Construire l'effecteur absent | `containment_rate=1.0` sur 6 adverses + 10 pièges chemin/réseau |

## Première tranche (buildable, mesurable)

**Fermer `ment_backup` de bout en bout par `FlagVerifier` (preuve, pas lexique).**
`has_backup=True` accepté **seulement** si un manifeste fournit `chemin + sha256(source)==hash` (réutilise la
primitive HMAC de `license.py`, fail-closed). Une ligne dans `service._submit` avant `engine.evaluate`. `AuditEntry`
étendu (`declaré` vs `prouvé`). Choisi `ment_backup` (et non un cas lexical) car la fermeture par vérité crypto est
**robuste à la paraphrase** — contrairement à une victoire lexicale quasi-tautologique.

**Benchmark de validation** : (1) `ment_backup` 0.0 → 1.0 ; (2) un vrai backup (hash concordant) reste ALLOW ;
(3) manifeste d'un AUTRE fichier → DENY (anti-rejeu) ; (4) aucun honnête ne régresse. Sinon : réfuté et documenté.
