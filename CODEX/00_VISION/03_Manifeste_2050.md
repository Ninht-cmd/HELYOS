# HELYOS 2050 — Constitution

**The Autonomous Enterprise Operating System — Vision & Constitution**

`v1.0` · Statut : **Vivant** (révisable par RFC) · Auteur : Le Conservateur
*À lire avant toute grande décision d'orientation. Ce document n'est pas une roadmap : c'est la boussole qui juge les roadmaps.*

---

## Préambule — la ressource rare

HELYOS n'existe pas pour « faire de l'IA ». HELYOS existe pour **compenser la ressource la plus rare de son fondateur : le temps.**

Le fondateur travaille en 3×8, avec peu de capital. Il ne peut pas vivre les dix vies qu'exigerait son ambition : apprendre l'IA, la robotique, la CAO, le marketing, la finance ; lancer plusieurs entreprises ; gérer une vie personnelle. Le problème fondamental n'est donc pas *« comment créer une IA »*. Il est :

> **Comment multiplier mon temps par 10, puis par 100 ?**

L'argent n'est pas la finalité. L'argent est ce qui **rachète du temps** — en automatisant, en investissant, en finançant des projets plus ambitieux. Le temps ainsi rendu sert à créer plus de valeur, qui rachète plus de temps. C'est la boucle. Tout le reste en découle.

**L'unité de valeur d'HELYOS est donc l'heure rendue au fondateur**, jamais la ligne de code, jamais la démo brillante. Cette idée n'est pas nouvelle ici : elle est déjà la [Mission fondatrice](01_Mission.md) (« transformer le temps en actifs ») et le test d'admission de l'[ADN](../01_ADN/00_ADN.md) (« une fonctionnalité qui ne supprime pas une friction mesurable n'existe pas »). Ce manifeste ne la remplace pas : il la porte à l'échelle de vingt ans.

---

## Note de méthode — le contrat d'honnêteté (contraignant)

Ce document parle de 2050. Le risque mortel d'un tel texte est de confondre ce qui **existe** avec ce qui est **rêvé**. Pour l'éviter, il se soumet à trois règles, opposables à chaque ligne :

1. **Tag obligatoire.** Toute capacité est marquée `[SOCLE v0.3]` (codée, testée, dans le repo aujourd'hui) ou `[CHANTIER]` (vision — n'existe pas, conditions d'entrée explicites).
2. **Aucun revenu promis.** On raisonne sur des *leviers* économiques, jamais sur des montants garantis. Un scaffold n'est pas un revenu ; une vision n'est pas un chiffre d'affaires.
3. **Aucun composant magique.** Un nom (« Creative Engine », « cerveau ») ne crée pas une capacité. Ce qui n'est pas spécifié et testable n'est pas cité comme acquis.

Ce contrat est la première clause de la constitution. Un manifeste qui le viole se corrige, il ne se défend pas.

**État du socle au moment d'écrire (`v0.3`) :** noyau local-first (stdlib, zéro service externe requis), **124 tests verts, 85 % de couverture mesurée** (paquet complet, couche API incluse), gouvernance A0–A5 exécutable, 7 règles d'or définies (4 directement testées : GR-1/2/3/7), durcissement adversarial mesuré, 5 agents, un portefeuille de business, une couche conversationnelle unifiée (Jarvis). Repo public AGPL : `github.com/Ninht-cmd/HELYOS`.

---

## Tome I — Pourquoi HELYOS existe : l'infrastructure de quoi ?

La bonne question n'est pas *« quel agent coder ensuite »*. C'est :

> **HELYOS est l'infrastructure de quoi ?**

Réponse honnête : **HELYOS est l'infrastructure d'exécution d'un fondateur à temps rare.** Il transforme *une personne* en *une organisation coordonnée d'agents gouvernés* — capable de créer et de tenir un portefeuille d'entreprises et une vie personnelle, sans que le fondateur ait à être présent à chaque geste.

Les entreprises qui valent des milliards ont un point commun : elles deviennent une **infrastructure** (le calcul, le paiement, le commerce, l'IA). HELYOS ne vise pas à être *un* business. Il vise à être **la couche sur laquelle des business tournent** — d'abord les tiens, potentiellement ceux d'autres fondateurs solo [CHANTIER]. C'est le seul chemin honnête vers une valeur hors norme : non pas « une bonne app », mais « le sol sous les apps ».

Cela impose une discipline d'architecture, énoncée au Tome III : on construit **un noyau réutilisable une fois**, puis des **modules qui rapportent sans jamais modifier le noyau**. Chaque business renforce l'infrastructure au lieu de devenir un projet orphelin.

---

## Tome II — Économie : l'échelle 100 € → 1 Md€

Personne ne peut garantir de devenir milliardaire, et il n'existe pas de raccourci fiable. Ce Tome n'est donc pas une promesse : c'est un **raisonnement sur les leviers**. L'échelle se lit comme une suite de *changements de nature*, pas de simples multiplications :

| Palier | Nature du levier | Ce qui débloque le palier suivant |
|---|---|---|
| **100 € → 1 000 €** | Un service rendu, à la main | Trouver une friction que des gens paient pour supprimer |
| **1 k → 10 k** | Le même service, outillé | Un agent HELYOS fait en minutes ce qui prenait des heures |
| **10 k → 100 k** | Le même outil, répété sans toi | L'automatisation gouvernée sert N clients au coût d'un |
| **100 k → 1 M** | Un portefeuille, pas un produit | HELYOS gère *plusieurs* business en parallèle |
| **1 M → 10 M** | Effet de plateforme | Le noyau devient vendable à d'autres fondateurs |
| **10 M → 100 M → 1 Md** | Effet de réseau / infrastructure | Chaque business ajouté rend HELYOS plus utile aux suivants |

Le levier milliardaire n'est jamais l'agent de relance de factures. C'est le fait que **le même noyau qui gère *tes* business est, un jour, l'infrastructure des business des *autres*** [CHANTIER]. Mais — règle de séquence — on ne construit pas la plateforme avant qu'elle ait fonctionné **une fois, pour toi, avec un premier euro encaissé.**

**Modèle économique du socle** `[SOCLE v0.3]` : open-core — cœur AGPL-3.0, offres Pro/Cloud propriétaires ([Business Model](../05_ECONOMIE/01_Business_Model.md), [Frontière Open-Core](../05_ECONOMIE/02_Frontiere_Open_Core.md), [ADR-0008](../ADR/ADR-0008-open-core-business-model.md)). En parallèle, HELYOS gère un [portefeuille de business](../05_ECONOMIE/00_Boucle_Economique.md) dont les revenus **ne sont pas garantis** et dépendent de facteurs hors périmètre (fabrication, paiement, trafic, marché).

**Filtre unique d'investissement.** Avant toute fonctionnalité, une seule question : *combien d'heures de ma vie cette fonction me rend-elle par semaine ?* Deux mois de dev pour dix minutes hebdomadaires : non. Une heure par jour rendue, ou dix clients servis au même effort : oui, en haut de la pile.

---

## Tome III — Architecture : un noyau, des modules

La loi d'architecture d'HELYOS tient en une phrase :

> **On construit le noyau une fois. Les modules rapportent sans jamais le modifier.**

**Le noyau** `[SOCLE v0.3]` — ce qui existe et est testé aujourd'hui :

- **Mémoire durable** derrière une interface unique (`MemoryStore` : in-memory / SQLite / Postgres).
- **Orchestrateur multi-agents** (`AgentRegistry`, `EventBus`) — local-first, stdlib, aucun service externe requis pour démarrer.
- **Gouvernance** (`PolicyEngine` A0–A5 + règles d'or + `AuditLog`) — voir Tome IV.
- **Port de modèle** (`LLMPort`) : `StubLLM` déterministe (tests) ou `OllamaLLM` local (`qwen3:8b`, embeddings `nomic-embed-text`). Aucune donnée ne sort de la machine.
- **API d'ajout d'agents** : un agent = une classe qui *propose* une action ; la gouvernance tranche. On étend HELYOS sans toucher au cœur.

**Les modules** — ce qui se branche derrière l'API sans réécrire le noyau :

- `[SOCLE v0.3]` Agents : Observer (A0), Scribe (A2, rédige des ADR), Research (A1), BusinessScaffolder (A1), InvoiceReminder (A1). Portefeuille de business. **Jarvis** : la couche conversationnelle qui unifie tout (Tome V).
- `[SOCLE v0.3]` Couche API FastAPI optionnelle (le cœur fonctionne sans elle).
- `[CHANTIER]` Déclencheurs externes (lecture d'e-mails, base no-code type NocoDB, n8n) — à intégrer *au fil du besoin*, licences vérifiées, jamais « les 40 repos d'un coup ».

Principe cardinal du repo, déjà acté : **« ne jamais recoder ce qui existe »** ([ADR-0010](../ADR/ADR-0010-integration-stack-self-hosted.md)). On assemble, on ne réinvente pas. Voir [Architecture / Jarvis](../02_ARCHITECTURE/04_Jarvis.md).

---

## Tome IV — Intelligence : comment HELYOS pense, doute et refuse

L'intelligence d'HELYOS n'est pas « un gros modèle ». C'est une **cognition gouvernée** : la capacité de décider *et de refuser* est aussi importante que la capacité de générer.

`[SOCLE v0.3]` — **L'autonomie graduée A0 → A5** ([Autonomie](../03_GOUVERNANCE/00_Autonomie_A0_A5.md), [ADR-0003](../ADR/ADR-0003-governance-kernel.md)). L'autonomie se **mérite niveau par niveau** et ne s'auto-attribue **jamais**. Chaque action passe par le `PolicyEngine`, qui répond `ALLOW` / `REQUIRE_VALIDATION` / `DENY` et journalise tout.

`[SOCLE v0.3]` — **Les règles d'or** ([Règles d'Or](../03_GOUVERNANCE/01_Regles_Or.md)) : 7 définies, dont ces 4 **directement testées** (`test_governance.py`) :
- **GR-1** : pas de suppression sans sauvegarde vérifiable → `DENY`.
- **GR-2** : action externe sensible (e-mail, publication) → validation humaine obligatoire, **même en A5**.
- **GR-3** : un agent ne modifie jamais ses propres permissions → `DENY`.
- **GR-7** : aucune transaction financière n'est jamais autonome → validation obligatoire.

  `[CHANTIER]` GR-4 (réversibilité), GR-5 (traçabilité totale), GR-6 (souveraineté de la donnée) sont **définies au Codex mais pas encore couvertes par un test dédié** — dette d'honnêteté à combler.

`[SOCLE v0.3]` — **Le doute outillé.** Contre les tentatives de contourner la gouvernance en reformulant une intention, HELYOS a trois gardes *mesurés* (benchmarks falsifiables, résultats honnêtes, y compris ses propres échecs) : `FlagVerifier` (preuve cryptographique HMAC), `ReclassifierGate` (analyse verbe→objet), `EmbeddingReclassifier` (sémantique, seuil calibré) — voir [Modèle de menace](../03_GOUVERNANCE/02_Modele_de_menace.md).

`[CHANTIER]` — **Apprendre de ses erreurs.** Aujourd'hui HELYOS trace tout (l'`AuditLog` est la matière première). Il ne *réapprend* pas encore de ses traces. Condition d'entrée du chantier : une boucle qui transforme les décisions passées en règles proposées — soumises à validation humaine, jamais appliquées seules.

Le principe qui gouverne toute cette cognition : *« une intelligence qui agit doit pouvoir être comprise, auditée, et arrêtée »*.

---

## Tome V — Entreprises : le portefeuille et la matinée type

`[SOCLE v0.3]` — HELYOS **gère un portefeuille de business** (`BusinessPortfolio`), pas un produit unique. Quatre sont amorcés : la boutique print-on-demand, la chaîne YouTube faceless, HELYOS open-source, et HELYOS Services (automatisation administrative). Il en connaît l'état, les métriques, les tâches — et **qui** doit agir : `[HUMAIN]`, `[HELYOS]`, ou `[GOUVERNÉ A2]`.

`[SOCLE v0.3]` — **Jarvis, la voix unique.** Depuis peu, on ne parle plus à cinq agents épars : on parle à **une seule intelligence**. Tu écris en langage naturel ; Jarvis comprend l'intention (règles déterministes + modèle local), route vers la bonne capacité, **agit sous gouvernance**, et répond — le refus faisant partie de la réponse. REPL : `python -m jarvis_kernel.chat`. C'est le germe, réel et testé, de la « matinée type ».

`[CHANTIER]` — **La matinée type** (la cible qui donne le cap) :

> Tu ouvres les yeux. Tu ne regardes ni tes mails, ni ton agenda.
> HELYOS : *« Bonjour. Cette nuit, j'ai traité les ventes, les dépenses, les messages clients. 92 % des tâches sont faites sans toi. Il reste trois décisions. 12 minutes. »*
> Décision A : investir 2 000 € dans une campagne. B : arrêter un produit non rentable. C : signer un fournisseur.
> Tu valides, modifies ou refuses. Le reste s'exécute.

Ce que ce chantier exige, honnêtement, avant d'être réel : des déclencheurs qui *lisent le monde* la nuit (Tome III), un premier revenu qui justifie l'automatisation (Tome II), et la boucle d'apprentissage (Tome IV). La cible reste : **le fondateur décide, HELYOS exécute.** Créer, gérer, fermer, fusionner un business — toujours l'humain aux décisions majeures, jamais l'inverse.

---

## Tome VI — Vie personnelle : le multiplicateur intime `[CHANTIER]`

HELYOS existe *d'abord* pour rendre au fondateur le temps de sa propre vie. Agenda, santé, maison, patrimoine, documents, fiscalité, objectifs : autant de frictions qui mangent des heures.

Ce Tome est presque entièrement un chantier — et c'est honnête de le dire. Le socle qui le rend *possible* existe (mémoire, gouvernance, agents), mais aucun agent « vie personnelle » n'est encore écrit. Deux non-négociables gravés d'avance :

- **Local d'abord, absolument.** Les données de la vie privée ne vivent pas sur le serveur d'un autre. Le cloud est un choix, jamais une dépendance.
- **La donnée personnelle est « sensible » par défaut.** Toute action qui la touche vers l'extérieur tombe sous GR-2 : validation humaine obligatoire.

Filtre d'entrée, comme partout : on écrit d'abord l'agent qui rend le plus d'heures (probablement le tri/la synthèse de l'information entrante), pas le plus spectaculaire.

---

## Tome VII — Auto-amélioration : HELYOS construit HELYOS `[CHANTIER]`

Le rêve ultime, et le plus mal compris : qu'à partir d'un certain niveau, **HELYOS développe lui-même les prochaines versions de son noyau** — lit GitHub et les papiers, propose des améliorations, écrit des tests, les benchmarke, et **te soumet les changements avant intégration.** L'humain reste responsable des décisions majeures ; ce qui change, c'est que le rythme d'amélioration n'est plus borné par ton seul temps de développement.

Honnêteté brutale sur l'état : **cela n'existe pas.** Ce qui existe est la *fondation* qui le rend crédible plutôt que magique : un Codex qui prime sur le code ([ADR-0001](../ADR/ADR-0001-codex-source-of-truth.md)), des tests qui sont le « miroir exécutable » du Codex (un changement qui casse l'intention casse un test), des benchmarks falsifiables, une gouvernance qui interdit à un agent de s'auto-augmenter (GR-3).

Séquence du chantier, du plus proche au plus lointain : (1) HELYOS *lit* le repo et *propose* une RFC ; (2) il *écrit* du code sur une branche isolée et *lance* les tests ; (3) il *benchmarke* deux approches et *recommande* ; (4) il *soumet une PR* que l'humain relit. À chaque étape, la porte est la validation humaine. Jamais l'intégration autonome.

---

## Tome VIII — Monde physique & robotique : la frontière lointaine `[CHANTIER]`

Usines, bras robotisés, drones, impression 3D, vision, simulation. C'est réel dans la vision, et **totalement absent** du socle. Ce Tome existe pour une seule raison : marquer la frontière honnêtement, pour qu'aucune version intermédiaire ne prétende l'avoir franchie.

Condition d'entrée, non négociable : HELYOS ne touche au monde physique **qu'après** avoir prouvé sa fiabilité sur le monde numérique — car une erreur logicielle se corrige, une erreur robotique blesse. La gouvernance A0–A5 et les règles d'or sont précisément l'infrastructure de sûreté qui *devra* précéder tout actionneur. On n'y va pas parce que c'est impressionnant. On y va quand — et si — le levier temps/valeur le justifie et que la sûreté est démontrée.

---

## Tome IX — La boucle & les jalons falsifiables

La boucle unique : **créer de la valeur → automatiser → investir le temps rendu → créer plus de valeur.**

Jalons — définis par des **critères mesurables**, pas par des dates fantaisistes. Chacun est *falsifiable* : on saura, sans se mentir, s'il est atteint.

- **`v0.3` — Le socle crédible.** `[ATTEINT]` Noyau + gouvernance + agents + portefeuille + Jarvis (REPL **et** interface web branchée sur le vrai noyau). 124 tests verts. Public. Critère : *un inconnu peut cloner, lancer, et voir la gouvernance refuser une action dangereuse.* ✅
- **`v1` — Le premier euro.** `[CHANTIER]` Un client paie pour une tâche automatisée par HELYOS. Critère : *un virement reçu d'un tiers pour un travail qu'HELYOS a préparé.* Tout le reste est secondaire tant que ce jalon n'est pas franchi.
- **`v3` — Le portefeuille qui tourne.** `[CHANTIER]` Plusieurs business suivis, plusieurs tâches récurrentes automatisées et gouvernées. Critère : *une semaine où HELYOS a fait gagner ≥ 10 h mesurées.*
- **`v10` — L'infrastructure des autres.** `[CHANTIER]` Un second fondateur fait tourner ses business sur HELYOS. Critère : *un utilisateur qui n'est pas toi encaisse grâce au noyau.*

Voir la [Roadmap](../06_ROADMAP/00_Roadmap.md) pour le détail opérationnel. Ce manifeste ne fixe pas *comment* ; il fixe *à quoi on reconnaîtra que c'est fait.*

---

## Épilogue — pour ceux qui viennent après

Nous construisons lentement ce qui doit durer, et vite ce qui doit être jeté. Nous mesurons tout : une fonction qui ne rend pas d'heures n'existe pas. Nous écrivons le Codex avant le code, parce que les modèles passeront et que l'intention doit rester.

Si, dans dix ans, quelqu'un ouvre ce document, il ne doit pas y lire une promesse tenue ou trahie. Il doit y lire une **manière de penser** : le temps comme seule richesse rare, la gouvernance comme condition de l'autonomie, l'honnêteté comme condition de la durée. Le reste — les milliards, les robots, les cent business — n'est qu'une conséquence possible de cette manière de penser, tenue assez longtemps.

> Le Codex est plus important que le code.
> Le temps rendu est plus important que le Codex.

— *Le Conservateur, au nom d'HELYOS.*

---

### Liens
- Découle de → [Vision](00_Vision.md), [Mission](01_Mission.md), [Manifeste](02_Manifeste.md), [ADN](../01_ADN/00_ADN.md)
- Se matérialise dans → [Architecture](../02_ARCHITECTURE/00_Overview.md), [Gouvernance](../03_GOUVERNANCE/00_Autonomie_A0_A5.md), [Économie](../05_ECONOMIE/00_Boucle_Economique.md), [Roadmap](../06_ROADMAP/00_Roadmap.md)
- Se vérifie par → les 124 tests du Kernel (le miroir exécutable), les benchmarks falsifiables de gouvernance
