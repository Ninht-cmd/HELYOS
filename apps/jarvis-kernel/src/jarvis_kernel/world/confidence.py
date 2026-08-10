"""HELYOS — Confiance composite métacognitive : C = E × R × A × F.

E = qualité de la preuve · R = fiabilité de l'analyseur · A = calibration de l'agent ·
F = fraîcheur de la source. Deux lectures : produit STRICT (un maillon faible écrase —
pour les actions sensibles) et moyenne GÉOMÉTRIQUE (qualité globale du diagnostic).

Points clés (d'après la spec du fondateur) :
  • R et A par PRIOR BAYÉSIEN (α=β=2) : 1/1 ne vaut pas 1.0 mais 0.60.
  • F par DEMI-VIE dépendant du TYPE de source (métadonnées 7 j, code 30 j, CI 6 h…).
  • Trois niveaux distincts : observation (le fait est-il vrai ?) · diagnostic (est-ce un
    vrai problème ?) · action (la correction améliorera-t-elle ?).
  • GARDE-FOU : la confiance classe et explique ; elle ne contourne JAMAIS la gouvernance
    (une confiance de 0.999 ne saute pas GR-2).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

# Qualité de preuve par nature du finding (la nature prime sur la quantité).
# Le mapping tests STATIQUE est PRÉLIMINAIRE (faible) ; la couverture RUNTIME est une
# preuve d'exécution forte — mais pas 1.0 : « exécuté » n'est pas « testé avec assertion ».
CATEGORY_WEIGHT = {
    "architecture": 1.00, "broken_import": 0.98, "runtime_asserted": 1.00, "import_cycle": 0.95,
    "complexity": 0.92, "runtime_coverage": 0.90, "dead_code": 0.68,
    "untested": 0.60, "static_test_mapping": 0.55, "text_pattern": 0.45,
}
# Demi-vies (en jours) par type de source — PAS de constante globale.
HALF_LIVES = {"repo_metadata": 7.0, "source_code": 30.0, "ci": 0.25, "issue": 2.0,
              "market": 0.01, "default": 14.0}


def evidence_quality(category: str, n_evidence: int = 1) -> float:
    """Poids de la nature de preuve + petit bonus par preuve indépendante (borné à 1)."""
    base = CATEGORY_WEIGHT.get(category, 0.5)
    return round(min(1.0, base + 0.02 * max(0, n_evidence - 1)), 4)


def bayesian_reliability(confirmed: int, rejected: int, alpha: float = 2, beta: float = 2) -> float:
    """(confirmed+α) / (confirmed+rejected+α+β). Évite l'illusion 1/1 = 1.0 ; le prior
    s'efface avec l'expérience."""
    return round((confirmed + alpha) / (confirmed + rejected + alpha + beta), 4)


def source_freshness(age_days: float, source_type: str = "source_code") -> float:
    """F = 2^(−t/H). Une donnée vieille d'une demi-vie vaut 0.5."""
    H = HALF_LIVES.get(source_type, HALF_LIVES["default"])
    return round(2 ** (-(max(0.0, age_days)) / H), 4)


@dataclass
class CompositeConfidence:
    evidence_quality: float
    analyzer_reliability: float
    agent_calibration: float
    source_freshness: float
    similar_confirmed: int = 0
    similar_total: int = 0

    def _vals(self):
        return [self.evidence_quality, self.analyzer_reliability,
                self.agent_calibration, self.source_freshness]

    @property
    def strict(self) -> float:                     # un maillon faible écrase (actions sensibles)
        return round(math.prod(self._vals()), 4)

    @property
    def balanced(self) -> float:                   # qualité globale du diagnostic
        return round(math.prod(self._vals()) ** (1 / 4), 4)

    def levels(self) -> dict:
        """Trois confiances DISTINCTES (fait vrai ? · vrai problème ? · la correction aide ?)."""
        obs = self.evidence_quality
        diag = round((self.evidence_quality * self.analyzer_reliability) ** 0.5, 4)
        action = self.balanced
        return {"observation": obs, "diagnosis": diag, "action": action}

    def explain(self) -> str:
        L = self.levels()
        return (f"globale {self.balanced} · stricte {self.strict} | "
                f"preuve {self.evidence_quality} · analyseur {self.analyzer_reliability} · "
                f"agent {self.agent_calibration} · fraîcheur {self.source_freshness} | "
                f"niveaux : fait {L['observation']} · problème {L['diagnosis']} · action {L['action']}"
                + (f" | historique : {self.similar_confirmed}/{self.similar_total} confirmés"
                   if self.similar_total else ""))


# ------------------------------------------------------------------ dérivation des facteurs via la mémoire
def _resolved(memory):
    confirmed, rejected = [], []
    for d in memory.decisions.values():
        ratio = None
        if d.outcome_id:
            o = memory.outcomes[d.outcome_id]
            ratio = (o.observed / o.expected) if o.expected else None
        if d.status in ("confirmed", "validated", "executed") or ratio is not None and ratio >= 0.5:
            confirmed.append(d)
        elif d.status == "rejected" or (ratio is not None and ratio <= 0):
            rejected.append(d)
    return confirmed, rejected


def _tagged(decisions, tag):
    return sum(1 for d in decisions if tag in d.entities)


def analyzer_reliability(memory, category: str) -> tuple[float, int, int]:
    conf, rej = _resolved(memory)
    c, r = _tagged(conf, f"category:{category}"), _tagged(rej, f"category:{category}")
    return bayesian_reliability(c, r), c, r


def agent_calibration(memory, agent: str = "dev_agent") -> float:
    conf, rej = _resolved(memory)
    c = sum(1 for d in conf if d.agent == agent)
    r = sum(1 for d in rej if d.agent == agent)
    return bayesian_reliability(c, r)


def change_assurance(ci_ok: bool, diff_coverage: float, critical_path_coverage: float,
                     behavioral_ok: bool, analyzer_reliability: float = 0.6,
                     mutation_score: float = 1.0) -> float:
    """CHANGE assurance — 4e niveau de confiance : la MODIFICATION est-elle suffisamment
    PROUVÉE ? (≠ « la CI est verte »). Produit borné [0,1] :

        CI × couverture du diff × couverture des lignes critiques × sondes comportementales
           × fiabilité de l'analyseur × score de mutation.

    Le score de mutation mesure le POUVOIR DE DÉTECTION des tests (une ligne exécutée mais
    dont une mutation dangereuse survit n'est pas protégée). Il ne REMPLACE pas les autres
    preuves : il s'ajoute au produit (mutation_score=1.0 par défaut = neutre). Un maillon
    faible écrase. GARDE-FOU : cette mesure classe la qualité d'une modification ; elle ne
    contourne JAMAIS la gouvernance (une assurance de 0.99 ne saute pas GR-2)."""
    b = 1.0 if behavioral_ok else 0.4        # sonde en échec = pénalité forte, pas nulle (un seul signal)
    factors = [1.0 if ci_ok else 0.0, _clip(diff_coverage), _clip(critical_path_coverage),
               b, _clip(analyzer_reliability), _clip(mutation_score)]
    return round(math.prod(factors), 4)


def _clip(x: float) -> float:
    return max(0.0, min(1.0, float(x)))


def composite_for(finding: dict, memory=None, *, source_age_days: float = 0.0,
                  source_type: str = "source_code") -> CompositeConfidence:
    """Assemble la confiance composite d'un finding à partir de bases RÉELLES."""
    E = evidence_quality(finding.get("category", ""), len(finding.get("evidence", [])) or 1)
    if memory is not None:
        R, c, r = analyzer_reliability(memory, finding.get("category", ""))
        A = agent_calibration(memory, "dev_agent")
    else:
        R, c, r, A = 0.6, 0, 0, 0.6                # priors seuls, sans expérience
    F = source_freshness(source_age_days, source_type)
    return CompositeConfidence(E, R, A, F, similar_confirmed=c, similar_total=c + r)
