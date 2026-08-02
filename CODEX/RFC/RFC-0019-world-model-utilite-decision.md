# RFC-0019 — World Model + fonction d'utilité + décision (du LLM-qui-répond au système-qui-dirige)

- **Statut** : Accepted
- **Date** : 2026-08-02
- **Auteur** : Le Conservateur (« il n'est pas autonome ni fonctionnel — diagnostic d'architecture »)

## Le problème, nommé en ingénieur

Jusqu'ici, formellement, HELYOS était `Yₜ = f(Xₜ)` : un LLM qui **répond** à un
contexte, entouré de scripts. Quasi sans état. Pas de **modèle interne de
l'entreprise**, pas de **fonction d'utilité explicite**, pas de **boucle de
contrôle**. Il répond ; il ne dirige pas.

Un système de direction est un problème de **contrôle optimal sous incertitude** :
un état `Sₜ`, une utilité `U(Sₜ)`, une politique `π` qui maximise `E[Σ γᵗ U(Sₜ)]`.
Le LLM n'y est plus *le système* — il devient un **estimateur** qui alimente le modèle.

## Décision — la fondation, construite pour de vrai (pas des classes vides)

Package `world/` (Python pur, testé, branché sur l'état réel) :

1. **`model.py` — World Model probabiliste.** Chaque nœud est une *croyance*
   `N(valeur, σ²)` datée et sourcée, avec dépendances (graphe). Deux opérations en
   font autre chose qu'un dictionnaire :
   - `observe()` : **fusion bayésienne** de gaussiennes (précision-pondérée) —
     `μ* = (p₀μ₀+p₁μ₁)/(p₀+p₁)`, `σ* = √(1/(p₀+p₁))`. C'est le *Belief Update Engine*.
   - `derive()` : nœud calculé (ex. `runway = cash/burn`) avec **propagation
     d'incertitude** (jacobienne numérique au 1er ordre). L'incertitude se propage.
   - La confiance rapportée **décroît avec l'âge** (demi-vie ~14 j) et avec σ.

2. **`decision.py` — utilité U(S) explicite + politique π.** `U(S)` est un scalaire
   inspectable (chaque terme est **pondéré par la confiance** de la croyance : on
   n'agit pas fort sur une donnée incertaine). `Policy.decide()` applique le modèle
   d'effet de chaque action candidate à une **copie** du World Model, recalcule `U`,
   et classe par **ΔU espéré − coût** (argmax borné). Le LLM n'arbitre pas : la
   décision est numérique.

3. **`seed.py` — amorçage depuis l'état RÉEL** (caisse, prospection, connecteurs,
   risques paiement/juridique). Le connu exactement a σ faible ; l'estimé (burn,
   progrès) a σ large et confiance basse — honnêtement.

## Preuve (sur l'état réel, caisse 0 €)

`U(S) = −0,27`, dominé par le risque. La politique classe seule : **Gumroad (+0,137)
→ immatriculation (+0,136) → connecteurs → 1er client → vidéos (ΔU négatif)** — elle
**retrouve** les priorités du Pouls, et déclare « publier des vidéos » non rentable
maintenant (coût > gain). 15 tests dont la math exacte (fusion √50/√20, propagation
σ=1,251). Atteignable via l'intent `monde` (« quelle est ta décision ? »).

## Ce que ça n'est PAS encore (annoncé, pas caché)

Cette RFC pose les couches **Représentation + Décision (mono-pas)**. Restent, dans
l'ordre : planificateur multi-pas (HTN/GOAP/PDDL), simulation/scénarios, graphe
d'opportunités, optimiseur de portefeuille (convexe/robuste), pipeline de veille,
apprentissage bayésien des *résultats* (fermer la boucle Feedback→Learning). Chacun
sera une RFC quand il sera construit — jamais une classe vide entre-temps.

## Gouvernance

Inchangée : le World Model **observe et décide en proposition** (A1). Exécuter une
décision reste soumis à A0–A5 (GR-2/GR-7 : argent/envoi jamais sans validation).
Voir [[RFC-0018]] (le cerveau), [[RFC-0012]] (le vrai Jarvis).
