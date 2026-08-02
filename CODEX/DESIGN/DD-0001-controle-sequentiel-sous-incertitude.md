# DD-0001 — HELYOS comme contrôle séquentiel sous incertitude

*Document de conception (revue d'architecture). Objet : relier l'implémentation à un
cadre théorique unique, positionner chaque brique, la situer sur une échelle de
maturité, expliciter les hypothèses et limites, et tracer la feuille de route. Les
revendications sont volontairement conservatrices : un terme technique n'est employé
que si ses propriétés sont effectivement présentes.*

- **Statut** : Draft de recherche · **Date** : 2026-08-02 · **Auteur** : Le Conservateur + HELYOS
- **Portée** : couche décisionnelle (`world/`), pas l'infrastructure logicielle.

---

## 1. Quel problème mathématique le système résout-il ?

On pose HELYOS comme un problème de **décision séquentielle sous observabilité
partielle** — un POMDP. Soit le tuple `(X, A, O, T, Z, R, γ)` :

- `x_t ∈ X` : état latent de l'entreprise (non observé directement) ;
- `a_t ∈ A` : action ;
- `o_t ∈ O` : observation ;
- `T(x_{t+1} | x_t, a_t)` : dynamique de transition ;
- `Z(o_t | x_t)` : modèle d'observation ;
- `R(x_t, a_t)` : récompense ;
- `γ ∈ [0,1)` : facteur d'actualisation.

L'état étant caché, l'agent agit sur la **croyance** `b_t(x) = P(x_t | o_{1:t}, a_{1:t−1})`,
mise à jour récursivement (filtre de Bayes) :

```
b_{t+1}(x') ∝ Z(o_{t+1} | x') ∑_x T(x' | x, a_t) b_t(x)          (prédiction + correction)
```

Le POMDP se réduit alors à un **MDP sur l'espace des croyances**, et l'objectif est

```
π* = argmax_π  E[ ∑_{t=0}^{T} γ^t R(x_t, a_t) ]
```

C'est le cadre unificateur. Tout composant se juge par sa place dans ce tuple et par
l'écart entre ce qu'il est et ce que le formalisme suppose.

---

## 2. Positionnement honnête de HELYOS dans le formalisme

La colonne « nature exacte » corrige les étiquettes trop généreuses — notamment :
ce que nous faisons n'est **pas** un filtre de Bayes sur état latent, mais une
**fusion de mesures** ; et rien n'**apprend** encore (la fusion met à jour des
croyances, pas le modèle).

| Élément du POMDP | Brique HELYOS | Nature exacte |
|---|---|---|
| État latent `x_t` | — | **Aucun état latent distinct des observations.** HELYOS croit directement sur des grandeurs observables (cash, prospects…). Il n'y a pas de `x` caché à inférer. |
| Modèle d'observation `Z(o\|x)` | connecteurs, `ledger`, `prospection`, APIs | Lectures directes (bruitées). Modèle d'observation ≈ **identité** (`H = I`), pas d'inférence sur un état caché. Couverture **partielle** (ex. `burn` non mesuré). |
| Croyance `b_t` | `world/model.py` | Croyance **factorisée gaussienne à covariance diagonale** (facteurs supposés indépendants) + nœuds dérivés (propagation linéarisée, jacobienne au 1er ordre). Pas de covariances croisées. |
| Mise à jour `b_{t+1}` | `observe()` | **Fusion de mesures gaussiennes** (produit de gaussiennes, précision-pondéré) — exacte, mais **statique** : aucune étape de prédiction/transition entre deux mesures. Ce n'est pas un filtre récursif au sens POMDP. |
| Transition `T` | `Action.effects` / `apply()` | Effets **déterministes, mono-pas, écrits à la main**. Pas de stochasticité, pas d'incertitude sur l'effet, non appris. |
| Récompense `R` | `decision.utility()` | Scalarisation **explicite, pondérée par la confiance**. Porte sur la **croyance** (moyennes + confiances), pas sur `x` latent — approximation de type **QMDP**. Poids **fixes**, non calibrés sur des résultats. |
| Politique `π` | `Policy.decide()` | **argmax glouton à horizon 1** sur un petit ensemble discret d'actions. Aucune recherche dans l'espace des croyances, aucun lookahead > 1. **Myope.** |
| Planification | — | **Absente.** |
| Apprentissage | — | **Absent.** La fusion met à jour des croyances ; elle ne met à jour **ni** `T` **ni** les poids de `R`. |
| Exécution | gouvernance A0–A5 | Couche d'action gouvernée présente ; les décisions du modèle sont des **propositions**, non auto-exécutées (GR-2/GR-7). |

**Conséquence honnête.** HELYOS est aujourd'hui un **contrôleur glouton à horizon 1
sur une croyance factorisée gaussienne mise à jour par fusion de mesures**, avec une
récompense heuristique explicite. C'est un point de départ propre et testé — pas un
solveur de POMDP.

---

## 3. Trois plans d'architecture (à ne pas confondre)

| Plan | Ce qui est présent | Ce qui manque |
|---|---|---|
| **Logiciel** (modules, API, persistance, orchestration) | packages `world/ agents/ business/ governance/ api/`, persistance SQLite, orchestrateur FastAPI, client/serveur MCP, 277 tests | — (le plus mûr) |
| **Cognitif** (représentation, mémoire, planification, décision, apprentissage) | représentation (croyance factorisée), mémoire persistante, décision (glouton) | **planification**, **apprentissage**, inférence sur état latent |
| **Décisionnel** (optimisation, contrôle, politique, gouvernance) | utilité explicite, contrôle glouton H=1, gouvernance A0–A5 | optimisation de politique, contrôle multi-horizon, calibration de l'objectif |

Dire « on a un World Model » est imprécis. Précisément : le plan **logiciel** est mûr,
le plan **décisionnel** existe en version mono-pas, le plan **cognitif** est le plus
incomplet (ni planification ni apprentissage).

---

## 4. Maturité (échelle L0–L5, inspirée des TRL)

`L0` concept · `L1` prototype algorithmique · `L2` implémentation fonctionnelle ·
`L3` validé sur scénarios contrôlés · `L4` validé sur données réelles · `L5` boucle
fermée en production.

| Capacité | Maturité | Justification (plus conservatrice que « ✅ ») |
|---|---|---|
| Représentation de croyance (gaussienne factorisée) | **L3** | Tourne sur l'état réel + tests exacts ; mais covariance diagonale, gaussiennes imposées. |
| Fusion de mesures (« belief update ») | **L2** | Math de fusion exacte et testée ; mais ce n'est pas un filtre récursif (pas d'étape de transition) → pas L4. |
| Fonction d'utilité `U(S)` | **L3** | Calcul validé sur données réelles ; **validité comme proxy de l'objectif non démontrée** (exige la boucle d'apprentissage) → pas L4. |
| Politique gloutonne (H=1) | **L3** | Implémentée, déterministe, testée ; **optimalité non validée** contre des résultats. |
| Simulation / modèle de transition | **L1** | Effets mono-pas écrits à la main, déterministes. |
| Planification multi-horizon | **L0** | Rien. |
| Découverte d'opportunités | **L0** | Rien. |
| Optimisation de portefeuille | **L0** | Rien (exige données de marché + solveur). |
| Apprentissage en ligne | **L0** | Rien n'apprend ; la fusion ≠ apprentissage de modèle. |

Écart assumé avec l'auto-évaluation initiale : « belief update » et « online learning »
étaient sur-cotés (L4/L1) ; ils sont ici **L2** et **L0**, car aucune donnée de
*résultat* ne valide encore le modèle de transition ni les poids de l'utilité.

---

## 5. Hypothèses et limites explicites

1. **Observabilité directe.** On suppose `o ≈ x` (modèle d'observation identité). Il
   n'y a pas d'inférence sur un état latent ; les grandeurs non mesurées (burn) sont
   des *a priori* à grande variance, pas des estimations filtrées.
2. **Indépendance des facteurs.** Covariance diagonale : les corrélations (cash↔revenu,
   risque↔clients) sont ignorées. Faux en général.
3. **Croyances gaussiennes.** Inadapté aux grandeurs bornées, discrètes ou multimodales.
   Traiter `risque ∈ [0,1]` ou un booléen « immatriculé » en gaussien est un pis-aller.
4. **Transition déterministe mono-pas.** Les effets d'action sont posés à la main, sans
   incertitude ni dépendance à l'état ; ils ne valent que pour un lookahead d'un pas.
5. **Myopie (H=1).** Pas d'affectation de crédit temporel : « investir maintenant,
   encaisser plus tard » n'est pris en compte que via des effets codés en dur.
6. **Récompense sur la croyance (QMDP-like).** Ignore la **valeur de l'information** :
   sans terme dédié, le système ne prend pas d'action *exploratoire* pour réduire son
   incertitude.
7. **Utilité fixe non calibrée.** Les poids de `U` sont un choix, non élicité et non
   validé comme proxy de l'objectif réel (100 k€).
8. **Stationnarité.** Aucun traitement de non-stationnarité / changement de régime.

---

## 6. Ce que nous NE revendiquons PAS

Ces termes ont des définitions précises ; les employer serait faux aujourd'hui.

- **« Résout un POMDP »** : non. Pas de planification dans l'espace des croyances, pas
  d'inférence sur état latent.
- **« Filtrage bayésien »** (au sens Kalman/particulaire récursif) : non. Fusion
  statique de mesures, sans étape de prédiction par `T`.
- **« World model »** (au sens model-based RL, Ha & Schmidhuber, Dreamer) : non. Aucune
  dynamique latente apprise ; « modèle du monde » est ici employé au sens faible de
  *graphe d'état probabiliste*, et c'est dit.
- **« Active Inference »** : non. Aucune minimisation d'énergie libre / EFE, aucune
  sélection d'action par free energy espérée, aucun modèle génératif sur états latents.
- **« Politique optimale »** : non. Sélection gloutonne à horizon 1, sans garantie.

---

## 7. Feuille de route : du contrôleur H=1 à l'agent adaptatif multi-horizon

Chaque phase indique le gain de maturité et le coût/risque. Les décisions restent des
**propositions** sous gouvernance A0–A5 tant que l'exécution n'est pas explicitement
autorisée.

**Phase A — Transition stochastique `T(b'|b,a)`.** Remplacer les effets déterministes
par des distributions d'effet ; ajouter une **étape de prédiction** (propager la
croyance à travers l'action). *Débloque le lookahead.* Simulation L1→L2, fusion→filtre
L2→L3. Coût : faible ; risque : spécifier des effets stochastiques crédibles.

**Phase B — Planification multi-horizon dans l'espace des croyances.** Rollout à
horizon reculé / échantillonnage parcimonieux ; départ bon marché en **QMDP**, puis
**POMCP/MCTS** sur croyances. Valeur = `∑ γ^t U(b_t)`. Planification L0→L2. C'est le
saut hors de la myopie. Coût : calcul (borner l'horizon) ; risque : explosion
combinatoire → élagage.

**Phase C — Apprentissage en ligne de `T` (et calibration de `U`).** Après exécution
de `a`, observer le `Δ` réel et mettre à jour le modèle d'effet (régression linéaire
bayésienne / conjugués) ; calibrer les poids de `U` sur les résultats (préférences
révélées). **Ferme la boucle Feedback→Learning.** Apprentissage L0→L2 ; utilité L3→L4.
C'est ici que le système devient *adaptatif*.

**Phase D — Valeur de l'information / perception active.** Récompenser la réduction
d'incertitude (ou la laisser émerger de la planification en croyance, qui valorise
naturellement l'information). Rapproche d'un comportement chercheur d'information —
**sans** revendiquer l'Active Inference ; si l'on adopte l'EFE, on le dira précisément.

**Phase E — Croyance plus riche.** Covariances croisées (graphe de facteurs) et
facteurs **non gaussiens** (Beta pour ratios/probabilités comme `risque`, Poisson pour
comptages), pour cesser d'abuser des gaussiennes. Représentation L3→L4.

**Transverse.** Découverte d'opportunités et optimisation de portefeuille deviennent des
modules spécialisés qui **lisent/écrivent la même colonne vertébrale de croyance** et
alimentent `U` — pas des greffes séparées.

---

## 8. Résumé en une phrase

HELYOS est, à ce jour, un **contrôleur décisionnel glouton à horizon 1** sur une
**croyance factorisée gaussienne** mise à jour par **fusion de mesures**, avec une
**récompense heuristique explicite** et une **gouvernance mûre** — et la feuille de
route ci-dessus est précisément l'ensemble minimal de briques (transition stochastique,
planification en croyance, apprentissage en ligne) qui le fait passer d'un *contrôleur
à un pas* à un *agent décisionnel adaptatif à horizon multiple*.

Voir [[RFC-0019]] (implémentation World Model + utilité + décision), [[RFC-0018]] (le cerveau).
