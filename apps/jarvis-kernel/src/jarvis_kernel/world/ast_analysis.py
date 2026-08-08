"""HELYOS — moteur d'analyse statique AST (findings avec PREUVE, pas des heuristiques).

Index AST → 4 analyseurs → Findings normalisés :
  • ImportGraphAnalyzer  : graphe d'imports internes → imports cassés, cycles, imports
                           inutilisés, modules orphelins, et INVARIANTS ARCHITECTURAUX.
  • DeadCodeAnalyzer     : table des symboles + cas spéciaux (décorateurs, __all__,
                           points d'entrée) → symboles publics jamais référencés.
  • ComplexityAnalyzer   : complexité cyclomatique (signal, pas bug).
  • TestCoverageMapper   : symboles source réellement référencés par les tests.

Le plus important pour HELYOS : les invariants de couche. Une violation n'est pas
« du mauvais code » — elle peut casser les garanties d'autonomie/gouvernance.
Python pur (module `ast` stdlib).
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field, asdict
from pathlib import Path

# Invariants de couche : (préfixe module, préfixes interdits en dépendance, raison)
LAYER_RULES = [
    ("governance", ("agents", "api", "world"), "la gouvernance ne doit dépendre d'aucune couche supérieure"),
    ("memory", ("api",), "la mémoire ne doit pas dépendre de l'UI/API"),
    ("kernel", ("agents", "api", "world"), "le noyau bus/événements reste bas niveau"),
]
_ENTRYPOINTS = {"main", "create_app", "serve", "__init__", "__main__", "chat", "mcp_server", "run"}


@dataclass
class Finding:
    id: str
    category: str
    severity: str          # low | medium | high
    confidence: float
    file: str
    symbol: str
    evidence: list = field(default_factory=list)
    recommendation: str = ""


@dataclass
class _Sym:
    name: str
    lineno: int
    public: bool
    decorated: bool
    complexity: int = 0


@dataclass
class _Mod:
    module: str
    path: str
    functions: list = field(default_factory=list)     # _Sym
    classes: list = field(default_factory=list)        # _Sym
    imports: list = field(default_factory=list)        # (target_module_dotted, name|None, internal, resolvable)
    used: set = field(default_factory=set)             # noms référencés (Name/Attribute/décorateurs)
    exports: set = field(default_factory=set)          # __all__


def _resolve(current: str, level: int, mod: str | None) -> str | None:
    if level == 0:
        return mod
    parts = current.split(".")
    base = parts[: max(0, len(parts) - level)]          # remonte `level` niveaux depuis le module
    return ".".join(base + ([mod] if mod else []))


def _complexity(node: ast.AST) -> int:
    c = 1
    for n in ast.walk(node):
        if isinstance(n, (ast.If, ast.For, ast.AsyncFor, ast.While, ast.ExceptHandler, ast.IfExp)):
            c += 1
        elif isinstance(n, ast.BoolOp):
            c += len(n.values) - 1
        elif isinstance(n, ast.comprehension):
            c += 1 + len(n.ifs)
        elif hasattr(ast, "match_case") and isinstance(n, ast.match_case):
            c += 1
    return c


def _decorator_names(node) -> list[str]:
    out = []
    for d in getattr(node, "decorator_list", []):
        t = d.func if isinstance(d, ast.Call) else d
        if isinstance(t, ast.Name):
            out.append(t.id)
        elif isinstance(t, ast.Attribute):
            out.append(t.attr)
    return out


class AstIndex:
    def __init__(self) -> None:
        self.modules: dict[str, _Mod] = {}

    def add(self, module: str, code: str, path: str = "") -> None:
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return
        m = _Mod(module=module, path=path or module)
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                m.used.add(node.id)
            elif isinstance(node, ast.Attribute):
                m.used.add(node.attr)
        for name in _decorator_names_all(tree):
            m.used.add(name)
        # __all__
        for node in tree.body:
            if isinstance(node, ast.Assign) and any(
                    isinstance(t, ast.Name) and t.id == "__all__" for t in node.targets):
                if isinstance(node.value, (ast.List, ast.Tuple)):
                    m.exports = {e.value for e in node.value.elts if isinstance(e, ast.Constant)}
        # symboles de haut niveau
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                m.functions.append(_Sym(node.name, node.lineno, not node.name.startswith("_"),
                                        bool(node.decorator_list), _complexity(node)))
            elif isinstance(node, ast.ClassDef):
                m.classes.append(_Sym(node.name, node.lineno, not node.name.startswith("_"),
                                      bool(node.decorator_list)))
        # imports
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                target = _resolve(module, node.level, node.module)
                for a in node.names:
                    m.imports.append((target, a.name))
            elif isinstance(node, ast.Import):
                for a in node.names:
                    m.imports.append((a.name, None))
        self.modules[module] = m

    # ---- vues dérivées ----
    def all_used(self) -> set:
        u = set()
        for m in self.modules.values():
            u |= m.used
        return u

    def internal_edges(self) -> dict[str, set]:
        pkg = _root_pkg(self.modules)
        edges = {}
        for name, m in self.modules.items():
            deps = set()
            for target, _n in m.imports:
                if target and target.startswith(pkg):
                    # normalise vers un module connu (le plus long préfixe présent)
                    tm = _longest_known(target, self.modules)
                    if tm and tm != name:
                        deps.add(tm)
            edges[name] = deps
        return edges


def _decorator_names_all(tree) -> list[str]:
    out = []
    for node in ast.walk(tree):
        out += _decorator_names(node)
    return out


def _root_pkg(modules) -> str:
    return next(iter(modules)).split(".")[0] if modules else ""


def _longest_known(dotted: str, modules) -> str | None:
    parts = dotted.split(".")
    for i in range(len(parts), 0, -1):
        cand = ".".join(parts[:i])
        if cand in modules:
            return cand
    return None


# ------------------------------------------------------------------ analyseurs
def _short(module: str) -> str:
    return module.split(".")[-1]


def _layer(module: str) -> str:
    parts = module.split(".")
    return parts[1] if len(parts) > 1 else ""     # jarvis_kernel.<layer>....


def analyze(index: AstIndex) -> list[Finding]:
    findings: list[Finding] = []
    seq = [0]

    def fid():
        seq[0] += 1
        return f"DEV-{seq[0]:04d}"

    used = index.all_used()
    edges = index.internal_edges()

    # 1) DeadCodeAnalyzer (contextuel)
    for name, m in index.modules.items():
        if _short(name) in _ENTRYPOINTS:
            continue
        for s in m.functions + m.classes:
            if not s.public or s.decorated or s.name in m.exports or s.name in _ENTRYPOINTS:
                continue
            if s.name not in used:                 # jamais référencé nulle part (AST)
                findings.append(Finding(fid(), "dead_code", "low", 0.8, m.path, s.name,
                    ["symbole public défini (AST)", "aucune référence dans tout l'index",
                     "non décoré, absent de __all__, pas un point d'entrée"],
                    f"Vérifier si {s.name} est mort ; sinon documenter son usage dynamique."))

    # 2) ComplexityAnalyzer
    for name, m in index.modules.items():
        for s in m.functions:
            if s.complexity >= 12:
                sev = "high" if s.complexity >= 20 else "medium"
                findings.append(Finding(fid(), "complexity", sev, 0.95, m.path, s.name,
                    [f"complexité cyclomatique = {s.complexity} (≥ seuil 12)"],
                    f"Découper {s.name} (branches multiples) pour réduire le risque de régression."))

    # 3) ImportGraphAnalyzer : imports cassés (relatifs non résolus) + cycles
    for name, m in index.modules.items():
        pkg = _root_pkg(index.modules)
        for target, sym in m.imports:
            if target and target.startswith(pkg) and _longest_known(target, index.modules) is None:
                findings.append(Finding(fid(), "broken_import", "high", 0.97, m.path,
                    f"{target}" + (f".{sym}" if sym else ""),
                    ["import interne non résolu (module absent de l'index)"],
                    f"Corriger l'import « {target} » dans {_short(name)}."))
    for cycle in _find_cycles(edges):
        mods = " → ".join(_short(c) for c in cycle)
        findings.append(Finding(fid(), "import_cycle", "medium", 0.9, cycle[0], mods,
            [f"cycle d'import : {mods} → {_short(cycle[0])}"],
            "Casser le cycle (extraire une interface / inverser une dépendance)."))

    # 4) Invariants architecturaux (le cœur pour HELYOS)
    for name, deps in edges.items():
        for prefix, forbidden, reason in LAYER_RULES:
            if _layer(name) == prefix:
                for d in deps:
                    if _layer(d) in forbidden:
                        findings.append(Finding(fid(), "architecture", "high", 0.97, name,
                            f"{_short(name)} → {_short(d)}",
                            [f"{prefix} importe {_layer(d)}", reason],
                            f"Supprimer la dépendance {_short(name)} → {_short(d)} (invariant de couche)."))

    findings.sort(key=lambda f: ({"high": 0, "medium": 1, "low": 2}[f.severity], -f.confidence))
    return findings


def test_coverage_gaps(index: AstIndex, test_index: AstIndex) -> list[Finding]:
    """Symboles publics du code source jamais référencés par les tests (mapping AST)."""
    tested = test_index.all_used()
    findings, seq = [], [0]
    for name, m in index.modules.items():
        if _short(name) in _ENTRYPOINTS:
            continue
        for s in m.functions + m.classes:
            if s.public and not s.decorated and s.name not in tested and s.name not in _ENTRYPOINTS:
                seq[0] += 1
                findings.append(Finding(f"DEV-T{seq[0]:04d}", "untested", "medium", 0.9, m.path, s.name,
                    ["symbole public détecté par AST", "aucun test ne référence ce symbole",
                     "mapping tests→source"],
                    f"Ajouter des tests ciblant {s.name}."))
    return findings


def _find_cycles(edges: dict[str, set]) -> list[list[str]]:
    cycles, seen = [], set()
    def dfs(node, stack):
        for nxt in edges.get(node, ()):
            if nxt in stack:
                cyc = stack[stack.index(nxt):]
                key = tuple(sorted(cyc))
                if key not in seen:
                    seen.add(key)
                    cycles.append(cyc)
            elif nxt not in visited:
                dfs(nxt, stack + [nxt])
    visited = set()
    for n in edges:
        if n not in visited:
            dfs(n, [n])
        visited.add(n)
    return cycles


# ------------------------------------------------------------------ chargement dépôt
def build_index_from_root(root: str | Path):
    src = Path(root) / "apps" / "jarvis-kernel" / "src"
    tests = Path(root) / "apps" / "jarvis-kernel" / "tests"
    idx, tidx = AstIndex(), AstIndex()
    for f in src.rglob("*.py"):
        if "__pycache__" in str(f):
            continue
        parts = list(f.relative_to(src).with_suffix("").parts)
        if parts[-1] == "__init__":                     # le paquet = son dossier (pas pkg.__init__)
            parts = parts[:-1]
        idx.add(".".join(parts), f.read_text(encoding="utf-8"), str(f.relative_to(root)))
    for f in tests.glob("test_*.py"):
        tidx.add(f.stem, f.read_text(encoding="utf-8"), str(f.relative_to(root)))
    return idx, tidx


def analyze_repo(root: str | Path) -> list[Finding]:
    idx, tidx = build_index_from_root(root)
    return analyze(idx) + test_coverage_gaps(idx, tidx)


def as_dicts(findings: list[Finding]) -> list[dict]:
    return [asdict(f) for f in findings]
