# HELYOS Ontology v1.0 — le modèle du monde complet

- **Statut** : Accepted (moteur implémenté + testé) · **Date** : 2026-08-02
- **Implémentation** : `world/ontology.py` · **Tests** : `tests/test_ontology.py` (9) · **Étend** : DD-0001, RFC-0019
- **Objet** : donner au noyau décisionnel un *monde* — les entités, leurs variables, leurs relations,
  la dynamique de leurs états, et la simulation des conséquences. « Le cerveau a désormais des organes. »

---

## 1. Pourquoi (le manque comblé)

Le noyau (RFC-0019 / DD-0001) sait **décider**, mais son monde se réduisait à 5 croyances
(`cash, risque, prospects, revenu, clients`). Un moteur de décision sur un monde pauvre reste aveugle.
L'ontologie définit **ce que HELYOS doit savoir gérer** : entreprises, produits, clients, fournisseurs,
marchés, actifs, machines, pièces, gens, infra — et **comment leurs états se propagent**.

Principe de conception : **ne pas dupliquer la colonne vertébrale probabiliste**. Chaque attribut
numérique d'une entité **est** une croyance du `WorldModel` (μ±σ, confiance, fusion bayésienne) ; les
relations sont des arêtes typées ; la simulation réutilise la propagation d'incertitude de `derive()`.
L'ontologie (types) est de la **donnée** (`default_ontology()` / JSON) : ajouter un domaine = éditer le
schéma, pas le moteur.

## 2. Le méta-modèle

```
Ontology  = (EntityType*, RelationType*)                 # le SCHÉMA (donnée)
EntityType = (name, {AttrSpec})                          # ex. Company, Supplier…
AttrSpec   = (name, kind, unit)                          # kind numérique -> croyance ; texte -> méta
RelationSpec = (name, inverse, semantics)                # dependency|impact|composition|flow|ownership|association
KnowledgeGraph = (Ontology, WorldModel, Entity*, Edge*)  # le graphe INSTANCIÉ
Entity     = (id, type, label, meta)                     # attrs numériques = croyances "id.attr"
Edge       = (src, relation, dst)
```

**Grounding probabiliste.** L'attribut numérique `X` de l'entité `e` est la croyance de clé `e.X` dans le
`WorldModel` : valeur, écart-type σ, confiance décroissante, mise à jour par fusion bayésienne. Les
attributs textuels/catégoriels (secteur, pays, matériau) vivent dans `Entity.meta` — le spine reste numérique.

**Intégrité.** `add_entity`, `set_attr`, `relate` **valident** contre l'ontologie : type, attribut et
relation doivent exister, sinon `ValueError`. Le graphe ne peut pas contenir d'entité mal typée.

## 3. Catalogue v1.0 — entités (16 types, 10 domaines)

| Domaine | Types | Attributs clés (croyances numériques + méta) |
|---|---|---|
| **Business** | `Company`, `Product`, `Service`, `Customer` | cash, mrr, revenus, couts, marge, croissance, clients, churn, cac, ltv, runway_mois, risque, reputation ; prix, cout_unitaire, unites_mois ; taille, valeur, satisfaction |
| **Finance/Trading** | `Asset`, `Position`, `Strategy` | prix, volume, volatilite, momentum, liquidite ; taille, entree, stop_loss, exposition, pnl ; performance, drawdown, probabilite |
| **Marché** | `Market`, `Competitor` | taille, croissance, urgence, concurrence, sentiment ; part_marche, force |
| **Supply** | `Supplier` | pays, unit_price, moq, delai_jours, fiabilite, risque_geo |
| **Engineering/Manufacturing** | `Part`, `Machine` | materiau, masse_g, cout_fab, resistance, tolerance_mm ; capacite, cout_horaire, rendement, taux_defaut |
| **Business Factory** | `Opportunity` | taille_marche, douleur, concurrence, cout_creation, delai_lancement, prob_succes, score |
| **Human/Org** | `Employee` | role, cout_mensuel, performance, disponible |
| **Infra** | `Infrastructure` | cout_cloud, utilisateurs, dispo, securite |
| **Connaissance** | `Knowledge` | confiance |

## 4. Catalogue v1.0 — relations (13 types)

`owns` · `produces` · `sells_to` · `supplied_by` · `employs` · `competes_with` · `targets` ·
`depends_on` · `impacts` · `uses` · `trades` · `composed_of` · `operated_by` — chacune avec son
**inverse** et sa **sémantique** (dependency / impact / composition / flow / ownership / association).

## 5. Dynamique & simulation des conséquences

Un attribut peut être **dérivé** d'attributs d'autres entités atteintes par relation
(`derive_attr(entity, attr, fn, inputs)`), p. ex. `Product.cout_unitaire = f(Supplier.unit_price)`,
`Company.marge = f(revenus, couts)`. La **simulation** est une intervention counterfactuelle :

```
simulate({ "foxconn.unit_price": 4.0 })     # do(x=4) : on POSE la valeur (pas de fusion)
  → recompute()                              # re-dérive la chaîne dans l'ordre de dépendance
  → renvoie l'avant/après de chaque nœud touché, σ propagé compris
```

**Preuve (chaîne fournisseur → marge), chiffrée et testée :**

```
do(prix fournisseur : 2 → 4 €)
  coque.cout_unitaire   3.20  → 6.40   (σ 1.76)
  biz.couts           320.00  → 640.0  (σ 176)
  biz.marge            78.7%  → 57.3%  (σ ±11.9 pt)      # chute de 21.3 points
```

C'est le patron « Tesla → batterie → lithium → Chine → prix → projet » : HELYOS **connaît** la
conséquence en traversant le graphe, incertitude comprise — sans qu'on la lui code au cas par cas.

## 6. Intégration avec le noyau décisionnel

- Les attributs étant des croyances, `world/decision.utility()` et `Policy.decide()` **lisent
  directement** le graphe (une action peut cibler `company.cash`, `product.prix`…).
- Une `Opportunity` porte un `score` — hameçon du futur **moteur de génération de business**
  (score = taille × urgence × marge × compétence × avantage).
- Détection de manque : si une compétence (`Employee.role`) requise par un projet est absente du graphe,
  HELYOS peut proposer (freelance, agent spécialisé, formation, embauche) — sous gouvernance A0–A5.

## 7. Portée honnête (ce que v1.0 EST et n'est PAS)

- **EST** : un moteur de graphe typé, réel et testé (intégrité + simulation multi-sauts chiffrée),
  posé sur la colonne vertébrale probabiliste ; un schéma v1.0 couvrant 16 types / 13 relations sur
  10 domaines ; la propagation de conséquences avec incertitude.
- **N'EST PAS (encore)** : le graphe **peuplé** de toutes les entités réelles (population = travail
  continu, alimenté par les connecteurs) ; les fonctions de dérivation ne sont pas **apprises** (posées
  à la main, cf. limite « transition » DD-0001) ; pas de raisonnement ontologique (inférence de type,
  subsomption) ni de résolution d'entités.

## 8. Feuille de route de l'ontologie

1. **Peuplement par les connecteurs** : GitHub/marché/Shopify écrivent des entités réelles (Company,
   Asset, Supplier) dans le graphe.
2. **Dérivations apprises** : remplacer les coefficients à la main par des relations calibrées sur les
   résultats (rejoint la Phase C de DD-0001 : apprentissage en ligne).
3. **Requêtes & chemins** : plus courts chemins d'impact, « qu'est-ce qui menace `biz.marge` ? ».
4. **Moteur d'opportunités** : scorer et classer les `Opportunity` (Business Factory).
5. **Non-gaussien** : attributs Beta (ratios/probabilités) et Poisson (comptages) — Phase E DD-0001.

Voir [[RFC-0019]] (World Model), [[DD-0001]] (contrôle sous incertitude),
[[HELYOS-Architecture-Specification-v1.0]] (spec consolidée).
