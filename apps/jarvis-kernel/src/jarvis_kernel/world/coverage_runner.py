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
    try:
        import coverage
    except ImportError:
        return {}
    import sys
    root = Path(root)
    src = root / "apps" / "jarvis-kernel" / "src"
    tests = root / "apps" / "jarvis-kernel" / "tests"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))            # jarvis_kernel importable par les tests
    cov = coverage.Coverage(source=[str(src / "jarvis_kernel")], branch=True, data_file=None)
    cov.start()
    try:
        suite = unittest.TestLoader().discover(str(tests), pattern=pattern, top_level_dir=str(tests))
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
                    "covered_lines": covered}
    return out
