"""HELYOS — mesure de couverture RUNTIME réelle via coverage.py.

Exécute la suite de tests sous instrumentation et renvoie, par fichier source :
lignes totales, lignes couvertes, % de couverture, et l'ensemble des lignes exécutées
(pour la couverture des lignes modifiées). Repli honnête si coverage.py est absent.
"""

from __future__ import annotations

import os
import unittest
from pathlib import Path


def measure_coverage(root: str | Path, pattern: str = "test_*.py") -> dict:
    """Couverture runtime du dépôt HELYOS (paquet jarvis_kernel)."""
    root = Path(root)
    src = root / "apps" / "jarvis-kernel" / "src"
    tests = root / "apps" / "jarvis-kernel" / "tests"
    return measure_coverage_paths(src, tests, pattern=pattern, source=str(src / "jarvis_kernel"),
                                  root=root)


def measure_coverage_paths(src_dir: str | Path, tests_dir: str | Path, *, pattern: str = "test_*.py",
                           source: str | None = None, root: str | Path | None = None) -> dict:
    """Mesure GÉNÉRIQUE : instrumente `source` en exécutant la suite de `tests_dir`, avec
    `src_dir` sur le sys.path. Renvoie par fichier : lignes totales, lignes couvertes,
    lignes EXÉCUTABLES (statements) et lignes couvertes — la base de la couverture de diff.
    Repli honnête ({}) si coverage.py est absent."""
    try:
        import coverage
    except ImportError:
        return {}
    import sys
    src_dir, tests_dir = Path(src_dir), Path(tests_dir)
    root = Path(root or src_dir)
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))            # paquet importable par les tests
    cov = coverage.Coverage(source=[source or str(src_dir)], branch=True, data_file=None)
    cov.start()
    try:
        suite = unittest.TestLoader().discover(str(tests_dir), pattern=pattern, top_level_dir=str(tests_dir))
        with open(os.devnull, "w") as null:
            unittest.TextTestRunner(verbosity=0, stream=null).run(suite)
    finally:
        cov.stop()
    data = cov.get_data()
    out = {}
    for f in data.measured_files():
        try:
            _fn, statements, _excl, missing, _disp = cov.analysis2(f)
        except Exception:
            continue
        total = len(statements)
        covered = sorted(set(statements) - set(missing))
        rel = os.path.relpath(f, root).replace("\\", "/")
        out[rel] = {"file": rel, "lines_total": total, "lines_covered": len(covered),
                    "coverage_pct": (len(covered) / total) if total else 0.0,
                    "covered_lines": covered, "executable_lines": sorted(statements)}
    return out
