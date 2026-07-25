"""Ingénierie mécanique — pièces 3D paramétriques (STL) + calculs, en Python PUR.

Ta machine n'a ni Blender ni CAD ni numpy. Mais le format STL s'écrit à la main
(des triangles), et les formules de méca sont de l'arithmétique. Donc HELYOS
*fait* de l'ingénierie sans rien installer : il génère une pièce .stl réelle
(ouvrable dans Blender / Cura / n'importe quel viewer) et calcule.

Honnêteté : c'est de la CAO paramétrique de base (boîte, cylindre, engrenage
simple) + des formules classiques — pas une simulation FEM. Le pas suivant
(rendu Blender, simulation scipy) exige d'installer Blender / numpy-scipy :
chantier assumé, une commande d'install.
"""

from __future__ import annotations

import math
import os
from pathlib import Path


def _tri(v1, v2, v3) -> str:
    # normale approx (produit vectoriel) — suffisant pour l'affichage/slicing
    ax, ay, az = (v2[0] - v1[0], v2[1] - v1[1], v2[2] - v1[2])
    bx, by, bz = (v3[0] - v1[0], v3[1] - v1[1], v3[2] - v1[2])
    nx, ny, nz = (ay * bz - az * by, az * bx - ax * bz, ax * by - ay * bx)
    n = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
    return (f"facet normal {nx / n:.4f} {ny / n:.4f} {nz / n:.4f}\nouter loop\n"
            f"vertex {v1[0]:.4f} {v1[1]:.4f} {v1[2]:.4f}\n"
            f"vertex {v2[0]:.4f} {v2[1]:.4f} {v2[2]:.4f}\n"
            f"vertex {v3[0]:.4f} {v3[1]:.4f} {v3[2]:.4f}\nendloop\nendfacet\n")


def _box(w: float, d: float, h: float) -> list:
    x, y, z = w / 2, d / 2, h
    c = [(-x, -y, 0), (x, -y, 0), (x, y, 0), (-x, y, 0),
         (-x, -y, z), (x, -y, z), (x, y, z), (-x, y, z)]
    q = [(0, 1, 2, 3), (7, 6, 5, 4), (0, 4, 5, 1),
         (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)]
    tris = []
    for a, b, cc, dd in q:
        tris += [(c[a], c[b], c[cc]), (c[a], c[cc], c[dd])]
    return tris


def _prism(radii_fn, teeth: int, h: float, segments: int) -> list:
    """Cylindre/engrenage : profil radial extrudé sur la hauteur h."""
    n = max(12, segments)
    top, bot = [], []
    for i in range(n):
        a = 2 * math.pi * i / n
        r = radii_fn(i, n)
        top.append((r * math.cos(a), r * math.sin(a), h))
        bot.append((r * math.cos(a), r * math.sin(a), 0.0))
    tris = []
    ct, cb = (0, 0, h), (0, 0, 0.0)
    for i in range(n):
        j = (i + 1) % n
        tris += [(bot[i], bot[j], top[j]), (bot[i], top[j], top[i])]   # flanc
        tris += [(ct, top[j], top[i])]                                 # dessus
        tris += [(cb, bot[i], bot[j])]                                 # dessous
    return tris


def generate_part(kind: str, params: dict, out_dir: str | os.PathLike | None = None) -> dict:
    """Génère une pièce 3D paramétrique et l'écrit en STL. Rend le chemin + le nb de triangles."""
    kind = (kind or "box").lower()
    p = {k: float(v) for k, v in (params or {}).items()
         if str(v).replace(".", "", 1).replace("-", "", 1).isdigit()}
    if kind in ("cylindre", "cylinder", "disque"):
        r = p.get("r", p.get("diametre", 20) / 2 if "diametre" in p else 20)
        tris = _prism(lambda i, n: r, 0, p.get("h", 10), int(p.get("segments", 48)))
    elif kind in ("engrenage", "gear", "pignon"):
        teeth = int(p.get("dents", p.get("teeth", 12)))
        r, tooth = p.get("r", 20), p.get("dent_h", 3)
        n = teeth * 4
        tris = _prism(lambda i, _n: r + (tooth if (i // 2) % 2 else 0), teeth, p.get("h", 6), n)
    else:  # box / plaque / bloc
        kind = "box"
        tris = _box(p.get("l", p.get("w", 40)), p.get("d", p.get("p", 20)), p.get("h", 10))
    body = "".join(_tri(*t) for t in tris)
    stl = f"solid helyos_{kind}\n{body}endsolid helyos_{kind}\n"
    out = Path(out_dir) if out_dir else Path(__file__).resolve().parents[5] / "pieces_3d"
    out.mkdir(exist_ok=True)
    path = out / f"{kind}.stl"
    path.write_text(stl, encoding="ascii")
    return {"kind": kind, "path": str(path), "triangles": len(tris),
            "note": "ouvrable dans Blender / Cura / tout viewer STL"}


def mechanical(kind: str, params: dict) -> dict:
    """Calculs de méca classiques (Python pur, sans numpy)."""
    p = {k: float(v) for k, v in (params or {}).items()}
    k = (kind or "").lower()
    if "engren" in k or "gear" in k or "ratio" in k:
        z1, z2 = p.get("z1", 1), p.get("z2", 1)
        return {"type": "rapport d'engrenage", "ratio": round(z2 / z1, 3) if z1 else None,
                "note": f"{z1} dents -> {z2} dents"}
    if "flexion" in k or "beam" in k or "poutre" in k:
        # flèche d'une poutre encastrée : delta = F L^3 / (3 E I)
        F, L, E, I = p.get("F", 0), p.get("L", 0), p.get("E", 210e9), p.get("I", 1e-8)
        delta = F * L ** 3 / (3 * E * I) if E * I else None
        return {"type": "flèche poutre encastrée (m)", "fleche_m": round(delta, 6) if delta else None}
    if "couple" in k or "torque" in k or "boulon" in k:
        # couple de serrage : C = K * F * d
        K, F, d = p.get("K", 0.2), p.get("F", 0), p.get("d", 0)
        return {"type": "couple de serrage (N·m)", "couple_Nm": round(K * F * d, 3)}
    return {"type": "inconnu", "aide": "types : engrenage(z1,z2) | poutre(F,L,E,I) | boulon(K,F,d)"}
