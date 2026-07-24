"""Bibliothèque open-source LOCALE — rendre utilisables les repos déjà téléchargés.

Le fondateur (via Codex) a téléchargé ~1 400 repos (OPEN-SOURCE-LAB + NVIDIA-LAB).
Sans index, c'est du poids mort. Ce module lit le catalogue local (TSV avec nom,
description, langage, étoiles) et le rend INTERROGEABLE : « quel repo pour faire X »
→ HELYOS cherche dans ce que TU as déjà, et dit lesquels sont clonés sur ton disque.

Honnêteté : avoir 1 400 repos n'est pas une richesse, c'est un entrepôt. La valeur,
c'est d'en trouver UN qui résout un vrai problème. Ce module sert exactement à ça —
transformer une collection dormante en une étagère où l'on trouve ce qu'on cherche.
"""

from __future__ import annotations

import csv
import os
from pathlib import Path


def _lab_root() -> Path:
    env = os.environ.get("OPEN_SOURCE_LAB_ROOT")
    for c in ([Path(env)] if env else []) + [
        Path.home() / "WORKSPACE" / "OPEN-SOURCE-LAB",
        Path(r"C:\Users\emezr\WORKSPACE\OPEN-SOURCE-LAB"),
    ]:
        if c.exists():
            return c
    return Path.home() / "WORKSPACE" / "OPEN-SOURCE-LAB"


class OpenSourceLibrary:
    def __init__(self, root: str | os.PathLike | None = None) -> None:
        self.root = Path(root) if root else _lab_root()

    def _catalog_tsv(self) -> Path | None:
        cat = self.root / "catalogs"
        if not cat.exists():
            return None
        tsvs = sorted(cat.glob("github-open-source-catalog-*.tsv"),
                      key=lambda p: p.stat().st_mtime, reverse=True)
        return tsvs[0] if tsvs else None

    def _rows(self) -> list[dict]:
        path = self._catalog_tsv()
        if path is None:
            return []
        try:
            with path.open("r", encoding="utf-8-sig", newline="") as f:
                return list(csv.DictReader(f, delimiter="\t"))
        except Exception:
            return []

    def _is_cloned(self, owner: str, name: str) -> bool:
        return (self.root / "github" / owner / name).is_dir()

    def count(self) -> int:
        return len(self._rows())

    def search(self, query: str, limit: int = 8) -> list[dict]:
        """Cherche dans le catalogue local. Score par mots du besoin dans nom+desc+topic,
        départage par étoiles ; marque ce qui est cloné localement."""
        tokens = [t for t in query.lower().split() if len(t) > 2]
        scored = []
        for r in self._rows():
            hay = " ".join([r.get("full_name", ""), r.get("description", ""),
                            r.get("source", ""), r.get("language", "")]).lower()
            score = sum(3 if t in r.get("full_name", "").lower() else
                        (1 if t in hay else 0) for t in tokens)
            if score <= 0:
                continue
            try:
                stars = int(r.get("stargazers_count", 0) or 0)
            except ValueError:
                stars = 0
            scored.append((score, stars, r))
        scored.sort(key=lambda x: (x[0], x[1]), reverse=True)
        out = []
        for _score, stars, r in scored[:limit]:
            owner, name = r.get("owner", ""), r.get("name", "")
            out.append({
                "full_name": r.get("full_name", ""),
                "description": r.get("description", ""),
                "language": r.get("language", ""),
                "stars": stars,
                "url": r.get("html_url", ""),
                "cloned_local": self._is_cloned(owner, name),
            })
        return out
