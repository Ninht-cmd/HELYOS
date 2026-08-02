"""HELYOS Model Governance — MLOps pour le World Model.

Une boucle d'apprentissage sans gouvernance des connaissances est dangereuse : on ne
sait plus pourquoi un coefficient a bougé, on ne peut pas revenir en arrière si une
série de données est corrompue, ni vérifier qu'un apprentissage améliore vraiment avant
de l'activer.

Cette couche versionne les lois apprises et répond à :
  • Pourquoi ce coefficient est passé de 1.42 à 1.58 ? quelles observations l'ont fait ?
  • Depuis quand cette version est-elle active ?
  • Ce nouveau modèle améliore-t-il ou dégrade-t-il (avant de le rendre actif) ?
  • Comparer deux modèles ; détecter une dérive ; revenir à une version antérieure.

Principe : historique **append-only** (comme l'AuditLog de gouvernance), promotion
**champion/challenger** validée sur un jeu tenu à part, activation explicite, rollback
traçable. La qualité des décisions dépend de cette traçabilité autant que de l'algo.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from .learning import CausalLaw, calibration


@dataclass
class LawVersion:
    version: int
    name: str
    coef_mean: float
    coef_sigma: float
    n_obs: int
    at: float
    note: str = ""
    provenance: dict = field(default_factory=dict)   # d'où vient cette version (batch, comparaison…)
    metrics: dict = field(default_factory=dict)       # évaluation au moment de l'enregistrement


@dataclass
class AuditRecord:
    at: float
    action: str          # register | promote | reject | rollback
    name: str
    version: int | None
    reason: str
    detail: dict = field(default_factory=dict)


class ModelRegistry:
    """Registre versionné des lois causales apprises (le « model registry » du World Model)."""

    def __init__(self, clock=None, bus=None) -> None:
        self._clock = clock or time.time
        self._bus = bus
        self.structure: dict[str, dict] = {}          # name -> {x_key, y_key, noise_sigma}
        self.versions: dict[str, list[LawVersion]] = {}
        self.active: dict[str, int] = {}
        self.audit: list[AuditRecord] = []

    def _log(self, action, name, version, reason, detail=None):
        self.audit.append(AuditRecord(self._clock(), action, name, version, reason, detail or {}))
        if self._bus is not None:
            try:
                self._bus.emit(f"model.{action}", name=name, version=version, reason=reason)
            except Exception:
                pass

    # ---- enregistrement ----
    def register(self, law: CausalLaw, *, note: str = "", provenance: dict | None = None,
                 metrics: dict | None = None, activate: bool = True) -> LawVersion:
        self.structure.setdefault(law.name, {"x_key": law.x_key, "y_key": law.y_key,
                                             "noise_sigma": law.noise_sigma})
        vs = self.versions.setdefault(law.name, [])
        v = LawVersion(len(vs) + 1, law.name, law.coef_mean, law.coef_sigma, law.n_obs,
                       self._clock(), note, dict(provenance or {}), dict(metrics or {}))
        vs.append(v)                                  # append-only : on n'écrase jamais l'historique
        self._log("register", law.name, v.version, note)
        if activate:
            self.active[law.name] = v.version
        return v

    def as_law(self, version: LawVersion) -> CausalLaw:
        s = self.structure[version.name]
        return CausalLaw(version.name, s["x_key"], s["y_key"], version.coef_mean,
                         version.coef_sigma, s["noise_sigma"], version.n_obs)

    def active_version(self, name: str) -> LawVersion | None:
        n = self.active.get(name)
        return next((v for v in self.versions.get(name, []) if v.version == n), None) if n else None

    def history(self, name: str) -> list[LawVersion]:
        return list(self.versions.get(name, []))

    # ---- promotion sous garde (champion / challenger) ----
    def propose(self, challenger: CausalLaw, val_pairs: list[tuple[float, float]], *,
                metric: str = "rmse", note: str = "") -> dict:
        """Évalue le challenger sur un jeu de validation TENU À PART, le compare au champion,
        et ne l'ACTIVE que s'il améliore la métrique. Sinon : enregistré mais non activé
        (champion conservé). C'est la validation avant mise en production."""
        name = challenger.name
        chal_m = calibration(challenger, val_pairs)
        champ_v = self.active_version(name)
        if champ_v is None:
            v = self.register(challenger, note=note or "modèle initial", metrics=chal_m)
            return {"decision": "promoted", "version": v.version, "reason": "aucun champion",
                    "metrics": chal_m}
        champ_m = calibration(self.as_law(champ_v), val_pairs)
        better = chal_m[metric] < champ_m[metric] - 1e-9
        prov = {"vs_version": champ_v.version, f"champion_{metric}": champ_m[metric],
                f"challenger_{metric}": chal_m[metric]}
        v = self.register(challenger, note=note, metrics=chal_m, provenance=prov, activate=better)
        if better:
            self._log("promote", name, v.version,
                      f"{metric} {champ_m[metric]} -> {chal_m[metric]}", prov)
            return {"decision": "promoted", "version": v.version,
                    "reason": f"{metric} amélioré", "champion": champ_m, "challenger": chal_m}
        self._log("reject", name, v.version,
                  f"{metric} {chal_m[metric]} >= champion {champ_m[metric]}", prov)
        return {"decision": "rejected", "version": v.version,
                "reason": "pas d'amélioration — champion conservé", "champion": champ_m, "challenger": chal_m}

    def compare(self, name: str, va: int, vb: int, val_pairs) -> dict:
        """Compare les performances de deux versions sur un même jeu."""
        get = lambda n: next(v for v in self.versions[name] if v.version == n)
        return {f"v{va}": calibration(self.as_law(get(va)), val_pairs),
                f"v{vb}": calibration(self.as_law(get(vb)), val_pairs)}

    # ---- rollback ----
    def rollback(self, name: str, version: int, *, reason: str = "") -> None:
        if not any(v.version == version for v in self.versions.get(name, [])):
            raise ValueError(f"version inconnue : {name} v{version}")
        self.active[name] = version                   # l'historique reste intact
        self._log("rollback", name, version, reason or "retour manuel")

    # ---- dérive (model drift) ----
    def drift(self, name: str, recent_pairs, *, threshold: float = 1.5) -> dict:
        """Compare l'erreur récente à la RMSE enregistrée du modèle actif. Flag si l'erreur
        a nettement grossi (dérive) — signal qu'il faut ré-apprendre ou investiguer."""
        v = self.active_version(name)
        recent = calibration(self.as_law(v), recent_pairs)
        base = v.metrics.get("rmse")
        ratio = round(recent["rmse"] / base, 3) if base else None
        drifted = bool(ratio and ratio > threshold)
        return {"drifted": drifted, "recent_rmse": recent["rmse"], "base_rmse": base,
                "ratio": ratio, "recent_bias": recent["bias"]}

    # ---- provenance : « pourquoi ce coefficient a-t-il bougé ? » ----
    def explain(self, name: str, version: int | None = None) -> str:
        vs = self.versions.get(name, [])
        if not vs:
            return f"{name} : aucune version enregistrée."
        v = next((x for x in vs if x.version == version), vs[-1]) if version else self.active_version(name)
        prev = next((x for x in vs if x.version == v.version - 1), None)
        parts = [f"{name} = {v.coef_mean:.4f} (±{v.coef_sigma:.4f}), v{v.version}, "
                 f"{'active' if self.active.get(name) == v.version else 'inactive'}, {v.n_obs} obs."]
        if prev:
            parts.append(f"Passé de {prev.coef_mean:.4f} (v{prev.version}) à {v.coef_mean:.4f}.")
        if v.provenance:
            parts.append("Provenance : " + ", ".join(f"{k}={val}" for k, val in v.provenance.items()))
        if v.metrics:
            parts.append("Métriques : " + ", ".join(f"{k}={val}" for k, val in v.metrics.items()))
        return " ".join(parts)

    # ---- persistance ----
    def to_dict(self) -> dict:
        return {"structure": self.structure, "active": self.active,
                "versions": {n: [vars(v) for v in vs] for n, vs in self.versions.items()},
                "audit": [vars(a) for a in self.audit]}
