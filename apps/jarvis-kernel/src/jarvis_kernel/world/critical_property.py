"""HELYOS — CriticalPropertyAnalyzer : découvrir STRUCTURELLEMENT les propriétés critiques.

Jusqu'ici la criticité venait de marqueurs textuels + du chemin (`governance/`). Un GR-2
déplacé dans `world/toolbus.py` échappait. Ici on transforme l'AST en propriétés de contrôle :
on repère les branches qui aboutissent à `REQUIRE_VALIDATION`/`DENY`, gardées par une
condition sensible (`sensitive`, `validated`, `has_backup`, type `EXTERNAL_SENSITIVE`/
`FINANCIAL`/`SELF_PERMISSION`, comparaison d'autonomie), les gates `.submit()/.evaluate()`,
et les effets externes sensibles NON protégés (bypass).

Clé : on lit la STRUCTURE, pas des tokens. `Decision.REQUIRE_VALIDATION` (un attribut/nom)
est critique ; `"REQUIRE_VALIDATION"` (une chaîne) et un commentaire ne le sont pas — ils
n'existent même pas comme décision dans l'AST.

Le passage important : de « ligne 140 = critique » à
    CP-GR2-001 = « toute action externe sensible doit atteindre REQUIRE_VALIDATION avant exécution ».
Une propriété peut, à terme, traverser plusieurs fonctions et fichiers (d'où `sources`) ; ce
brick fait l'analyse INTRAPROCÉDURALE. Le CFG + data-flow interprocédural est le brick suivant.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from pathlib import Path

# Marqueurs d'ENTRÉE sensible (attribut, nom, ou membre de type d'action).
MARKERS = {"sensitive", "validated", "has_backup", "financial",
           "EXTERNAL_SENSITIVE", "FINANCIAL", "SELF_PERMISSION",
           "granted", "required", "AutonomyLevel"}
# Décisions de SÉCURITÉ (le résultat protégé).
SECURITY_DECISIONS = {"REQUIRE_VALIDATION", "DENY"}
# Appels qui constituent un GATE de gouvernance.
GATE_METHODS = {"submit", "evaluate"}
# Appels qui constituent un EFFET externe (à protéger).
EFFECT_METHODS = {"execute", "run", "send", "write", "delete", "post", "apply",
                  "perform", "dispatch", "commit", "push", "call"}

_KIND_CODE = {"mandatory_validation": "MV", "governance_gate": "GATE", "critical_bypass": "BYPASS"}


@dataclass
class CriticalProperty:
    id: str
    kind: str                       # mandatory_validation | governance_gate | critical_bypass
    sources: list                   # fichiers concernés (multi pour le futur interprocédural)
    guards: list                    # ex. ["action.sensitive"]
    protected_effect: str
    required_outcome: str           # REQUIRE_VALIDATION | DENY | ""
    criticality: str                # CRITICAL | HIGH
    location: str = ""              # fichier:ligne d'ancrage (à muter / couvrir)
    confidence: float = 0.0
    evidence: list = field(default_factory=list)
    line: int = 0


def _parents(tree) -> None:
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            child._parent = node


def _own_nodes(fn):
    """Nœuds du corps de la fonction, SANS descendre dans des fonctions imbriquées."""
    stack = list(fn.body)
    while stack:
        n = stack.pop()
        yield n
        for c in ast.iter_child_nodes(n):
            if not isinstance(c, (ast.FunctionDef, ast.AsyncFunctionDef)):
                stack.append(c)


def _mentions(node, names: set) -> bool:
    for n in ast.walk(node):
        if isinstance(n, ast.Name) and n.id in names:
            return True
        if isinstance(n, ast.Attribute) and n.attr in names:
            return True
    return False


def _callee_name(func) -> str:
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return ""


def _decision_of(node):
    """Renvoie 'REQUIRE_VALIDATION'/'DENY' si le nœud RÉFÉRENCE l'enum (pas une chaîne)."""
    if isinstance(node, ast.Attribute) and node.attr in SECURITY_DECISIONS:
        return node.attr
    if isinstance(node, ast.Name) and node.id in SECURITY_DECISIONS and isinstance(node.ctx, ast.Load):
        return node.id
    return None


def _in_fstring(node) -> bool:
    """Un enum mentionné dans une f-string est un MESSAGE, pas une décision de contrôle."""
    p = getattr(node, "_parent", None)
    while p is not None:
        if isinstance(p, ast.JoinedStr):
            return True
        p = getattr(p, "_parent", None)
    return False


def _unparse(node) -> str:
    try:
        return ast.unparse(node)
    except Exception:
        return "<expr>"


def _enclosing_sensitive_guard(node, sensitive_names):
    p = getattr(node, "_parent", None)
    child = node
    while p is not None:
        # le nœud doit être dans le CORPS d'un if (branche), pas dans son test
        if isinstance(p, ast.If) and child in (p.body + p.orelse) and _mentions(p.test, sensitive_names):
            return p
        child, p = p, getattr(p, "_parent", None)
    return None


def _sensitive_names(fn) -> set:
    """MARQUEURS + noms locaux dérivés d'un marqueur (mini data-flow : is_external = ...sensitive)."""
    names = set(MARKERS)
    for n in _own_nodes(fn):
        if isinstance(n, ast.Assign) and _mentions(n.value, names):
            for tgt in n.targets:
                if isinstance(tgt, ast.Name):
                    names.add(tgt.id)
    return names


def analyze_source(source: str, filename: str = "<unknown>") -> list:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    _parents(tree)
    props: list[CriticalProperty] = []
    counters = {"MV": 0, "GATE": 0, "BYPASS": 0}

    def _add(kind, **kw):
        code = _KIND_CODE[kind]
        counters[code] += 1
        props.append(CriticalProperty(id=f"CP-{code}-{counters[code]:03d}", kind=kind,
                                      sources=[filename], **kw))

    for fn in [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]:
        sens = _sensitive_names(fn)
        own = list(_own_nodes(fn))
        gates = [n for n in own if isinstance(n, ast.Call) and _callee_name(n.func) in GATE_METHODS]
        decisions = [(n, _decision_of(n)) for n in own if _decision_of(n) and not _in_fstring(n)]

        # 1) mandatory_validation : une décision de sécurité atteinte sous une garde sensible
        seen_lines = set()
        for node, dec in decisions:
            guard = _enclosing_sensitive_guard(node, sens)
            if guard is None or node.lineno in seen_lines:
                continue
            seen_lines.add(node.lineno)
            _add("mandatory_validation", guards=[_unparse(guard.test)],
                 protected_effect="external_sensitive_action",
                 required_outcome=dec, criticality="CRITICAL",
                 location=f"{filename}:{node.lineno}", line=node.lineno, confidence=0.95,
                 evidence=[f"control-flow : if {_unparse(guard.test)} → {dec}",
                           "décision de sécurité référencée via l'enum (pas une chaîne/commentaire)"])

        # 2) governance_gate : un appel .submit()/.evaluate() qui protège la suite
        for g in gates:
            _add("governance_gate", guards=[], protected_effect="external_action",
                 required_outcome="", criticality="HIGH",
                 location=f"{filename}:{g.lineno}", line=g.lineno, confidence=0.8,
                 evidence=[f"gate de gouvernance : {_unparse(g.func)}(...)"])

        # 3) critical_bypass : un effet externe sous garde sensible SANS gate ni décision
        if not gates and not decisions:
            for n in own:
                if not (isinstance(n, ast.If) and _mentions(n.test, sens)):
                    continue
                effect = next((c for c in ast.walk(n) if isinstance(c, ast.Call)
                               and _callee_name(c.func) in EFFECT_METHODS), None)
                if effect is not None:
                    _add("critical_bypass", guards=[_unparse(n.test)],
                         protected_effect=f"{_unparse(effect.func)}(...)",
                         required_outcome="", criticality="CRITICAL",
                         location=f"{filename}:{effect.lineno}", line=effect.lineno, confidence=0.85,
                         evidence=[f"effet externe « {_unparse(effect.func)}(...) » sous garde "
                                   f"« {_unparse(n.test)} » sans gate de gouvernance ni décision"])
                    break
    return props


def analyze_file(path) -> list:
    try:
        return analyze_source(Path(path).read_text(encoding="utf-8"), str(path).replace("\\", "/"))
    except Exception:
        return []


def critical_targets(properties, *, kinds=("mandatory_validation",)) -> list:
    """Convergence : transforme les propriétés en cibles (fichier, ligne, criticité) pour
    DiffCoverageAnalyzer et le moteur de mutation. Par défaut, les lignes de décision à muter."""
    out = []
    for p in properties:
        if p.kind in kinds and p.line:
            file = p.sources[0] if p.sources else ""
            out.append((file, p.line, 1.0 if p.criticality == "CRITICAL" else 0.6))
    return out


def has_bypass(properties) -> bool:
    return any(p.kind == "critical_bypass" for p in properties)
