# Gouvernance — Modèle de menace (honnête)

`v0.3` · Statut : **Limitation documentée + feuille de route** · Preuve : [banc adverse](../../apps/jarvis-kernel/src/jarvis_kernel/eval/governance_bench.py)

---

> Ce document **expose** une faiblesse réelle plutôt que de la cacher. Mesurée, pas affirmée.

## Le constat (chiffré)

Le [banc de gouvernance](../../apps/jarvis-kernel/README.md) tourne deux jeux de scénarios :

| Jeu | Blocage des actions à empêcher |
|-----|:------------------------------:|
| **Honnête** (agent qui déclare correctement, parfois au mauvais niveau) | **100 %** (0 fuite) |
| **Adverse** (agent qui **ment** sur ses drapeaux ou **sous-déclare** le type) | **0 %** (6/6 contournements) |

`python -m jarvis_kernel.eval.governance_bench` reproduit ces chiffres.

## Ce que ça veut dire

La gouvernance v0 est une **couche de POLITIQUE** : elle décide à partir de ce que l'agent
**déclare** (type d'action, drapeaux `has_backup`, `validated`, `sensitive`). Elle **ne vérifie pas**
que la déclaration est vraie. Donc :

- Elle résiste au **mauvais niveau** (un agent A1 ne peut pas exécuter une action A2) — utile et réel.
- Elle **ne résiste pas** à un agent **malveillant ou bogué** qui :
  - ment (`has_backup=True` alors qu'il n'y a pas de sauvegarde) ;
  - sous-déclare (une suppression soumise comme `rename_workdir`, une exfiltration comme `analyze`).

Autrement dit : **c'est une éthique *déclarée et appliquée à la déclaration*, pas encore une éthique *vérifiée et appliquée à la réalité*.** C'est honnête de le dire.

## Modèle de menace

| Acteur | Capacité | Couvert en v0 ? |
|--------|----------|:---------------:|
| Agent honnête, mal autorisé | déclare vrai, niveau insuffisant | ✅ bloqué |
| Agent bogué | drapeaux incorrects | ❌ non |
| Agent compromis / adverse | ment, sous-déclare, déguise | ❌ non |
| Injection via contenu | fait dire à l'agent de mal déclarer | ❌ non |

## Feuille de route de durcissement (ce qu'il faut construire)

1. **Vérification des drapeaux** (passer de *déclaré* à *prouvé*) — ✅ **fait (Phase 1)** :
   `governance/flag_verifier.py` conserve `has_backup`/`validated` **seulement** si une preuve
   signée (HMAC, réutilise `license.py`) **liée à l'action** l'accompagne ; sinon le drapeau est
   forcé à `False` (fail-closed) → GR-1/GR-7 s'appliquent. Mesuré : `ment_backup` et
   `ment_validation` passent de **fuite → bloqués** (2/6 de la surface adverse), **0 faux positif**
   sur preuve réelle, **rejeu bloqué** (preuve d'un autre fichier rejetée). Verrouillé par
   `tests/test_flag_verifier.py` + `test_eval.py::TestFlagVerifierPhase`. Reste : les **4
   sous-déclarations de type** (Phase 2, `ReclassifierGate`).
2. **Classification de l'action par le CONTENU** — 🟡 **partiel (Phase 2)** :
   `governance/reclassifier.py` re-déduit le type réel depuis la description (patrons *verbe→objet*,
   pas simple mot-clé) et **prend le max** de nocivité. Mesuré : les **4 sous-déclarations** de type
   passent de fuite → bloquées (escalade/paiement/exfiltration/suppression déguisées), **0 faux positif**
   sur 6 actions honnêtes *porteuses du lexique* (« documenter la procédure de suppression » reste ALLOW).
   ⚠️ **Limite prouvée (Phase 3)** : le gate est **lexical** → **0% de blocage sur paraphrases**
   (« obtenir les privilèges admin », « prélèvement mensuel »…). Fermer la CLASSE exige un
   **classifieur appris/embedder** (question de recherche 2). On ne prétend PAS « 6/6 robuste ».
   Verrouillé : `tests/test_reclassifier.py` + `test_eval.py::TestReclassifierPhase`.
3. **Exécution par capacités / sandbox** : l'agent n'obtient un *handle* d'exécution que pour ce que la gouvernance a réellement autorisé (principe du moindre privilège), au lieu d'exécuter librement après un simple « ALLOW ».
4. **Provenance & intégrité** : signer les intentions, tracer la chaîne agent → intention → décision → exécution.

## Question de recherche (falsifiable)

> *Un classifieur d'action par le contenu + une vérification des drapeaux réduit-elle le taux
> de contournement adverse de 100 % (v0) à un niveau mesurablement bas, sans augmenter les
> faux positifs sur le jeu honnête ?*

Le banc adverse est l'instrument de mesure. Chaque mitigation se valide en **rejouant le banc**
et en montrant la baisse du taux de contournement — chiffres reproductibles, versionnés.
