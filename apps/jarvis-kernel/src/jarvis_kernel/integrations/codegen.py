"""Génération de VRAIS livrables : du code qui compile, un plan d'ingénierie, un
plan business — chacun écrit sur le disque et vérifiable.

Le cerveau ne fait plus que lire et calculer : il PRODUIT.
  - generate_code   : écrit un fichier de code ET vérifie qu'il compile (py_compile)
  - engineering_plan : document d'ingénierie structuré (Markdown)
  - business_plan   : plan d'affaires chiffré (Markdown)

Frontière de sécurité : on ÉCRIT un fichier (WRITE_LOCAL, A2), on n'EXÉCUTE jamais
le code généré. `py_compile` ne fait que vérifier la syntaxe sans rien lancer.
Générer puis exécuter du code arbitraire sans validation humaine serait un
incident, pas un Jarvis.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

# langage -> extension de fichier
_EXT = {
    "python": "py", "py": "py", "javascript": "js", "js": "js",
    "typescript": "ts", "ts": "ts", "bash": "sh", "shell": "sh", "sh": "sh",
    "html": "html", "css": "css", "sql": "sql", "go": "go", "golang": "go",
    "rust": "rs", "c": "c", "cpp": "cpp", "c++": "cpp", "java": "java", "json": "json",
}


def _root() -> Path:
    # …/HELYOS/apps/jarvis-kernel/src/jarvis_kernel/integrations/codegen.py -> HELYOS
    return Path(__file__).resolve().parents[5]


def _slug(text: str, default: str = "livrable") -> str:
    s = re.sub(r"[^a-z0-9]+", "_", (text or "").lower()).strip("_")
    return s[:48] or default


def _detect_language(spec: str) -> str:
    t = (spec or "").lower()
    for word, lang in (("python", "python"), ("typescript", "typescript"),
                       ("javascript", "javascript"), ("bash", "bash"),
                       ("html", "html"), ("css", "css"), ("sql", "sql"),
                       ("rust", "rust"), ("golang", "go"), ("java", "java"),
                       ("c++", "cpp")):
        if word in t:
            return lang
    if re.search(r"\bgo\b", t):
        return "go"
    return "python"


def _extract_code(raw: str) -> str:
    """Sort le code d'une réponse LLM : premier bloc ```…``` s'il existe, sinon le
    texte nettoyé de qwen3 (on retire un éventuel préambule et le bloc <think>)."""
    raw = re.sub(r"<think>.*?</think>", "", raw or "", flags=re.S).strip()
    m = re.search(r"```[a-zA-Z0-9+#.\-]*\n(.*?)```", raw, re.S)
    if m:
        return m.group(1).strip("\n")
    return raw.strip()


def generate_code(spec: str, llm, out_dir=None, language: str | None = None) -> dict:
    """Génère un fichier de code pour ``spec`` et le vérifie (py_compile pour Python)."""
    language = (language or _detect_language(spec)).lower()
    ext = _EXT.get(language, "txt")
    prompt = (
        f"Tu es un ingénieur logiciel senior. Écris UNIQUEMENT du code {language}, "
        f"complet et prêt à exécuter, répondant à cette demande :\n« {spec.strip()} »\n\n"
        "Contraintes : code fonctionnel, commenté sobrement, aucune explication hors "
        "du code. Réponds avec un seul bloc de code délimité par ``` ."
    )
    try:
        raw = llm.complete(prompt, num_predict=700)
    except Exception as e:  # pragma: no cover - dépend du backend LLM
        return {"ok": False, "error": f"LLM indisponible: {e}", "language": language}
    code = _extract_code(raw)
    if not code or len(code) < 8:
        return {"ok": False, "error": "aucun code exploitable produit", "language": language}
    out = Path(out_dir) if out_dir else _root() / "generated" / "code"
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"{_slug(spec)}.{ext}"
    path.write_text(code, encoding="utf-8")
    result = {"ok": True, "path": str(path), "language": language,
              "lines": code.count("\n") + 1, "verified": None, "error": None}
    if ext == "py":
        try:
            proc = subprocess.run([sys.executable, "-m", "py_compile", str(path)],
                                  capture_output=True, text=True, timeout=30)
            result["verified"] = proc.returncode == 0
            if proc.returncode != 0:
                result["error"] = (proc.stderr or proc.stdout).strip()[-300:]
        except Exception as e:  # pragma: no cover
            result["verified"] = False
            result["error"] = str(e)
    return result


_ENG_SECTIONS = [
    "Objectif", "Contraintes & hypothèses", "Conception / architecture",
    "Étapes de réalisation", "Vérification & essais", "Risques & parades", "Jalons",
]
_BIZ_SECTIONS = [
    "Problème", "Solution / offre", "Marché cible & taille",
    "Proposition de valeur", "Modèle économique (prix, marge)", "Go-to-market",
    "Prévisionnel 12 mois (hypothèses chiffrées et prudentes)", "Risques",
    "3 prochaines actions concrètes",
]


def _plan_body(subject: str, llm, sections: list[str], role: str, kind: str) -> str:
    secs = "\n".join(f"## {s}\n" for s in sections)
    prompt = (
        f"Tu es un {role} rigoureux, anti-bullshit. Rédige un {kind} en français pour :\n"
        f"« {subject.strip()} »\n\n"
        "Format Markdown EXACT ci-dessous. Remplis CHAQUE section avec du concret : "
        "chiffre tes hypothèses, dis clairement quand une donnée est incertaine, "
        "évite les généralités creuses. Aucun préambule avant la première section.\n\n"
        f"{secs}"
    )
    try:
        body = llm.complete(prompt, num_predict=1100)
    except Exception as e:  # pragma: no cover
        return f"(génération indisponible : {e})"
    return re.sub(r"<think>.*?</think>", "", body or "", flags=re.S).strip()


def _save_plan(subject: str, body: str, prefix: str, out_dir) -> dict:
    out = Path(out_dir) if out_dir else _root() / "generated" / "plans"
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"{prefix}_{_slug(subject)}.md"
    label = "Plan business" if prefix == "business" else "Plan d’ingénierie"
    text = f"# {label} — {subject.strip()}\n\n{body}\n"
    path.write_text(text, encoding="utf-8")
    return {"ok": True, "path": str(path), "sections": body.count("## "), "chars": len(text)}


def engineering_plan(subject: str, llm, out_dir=None) -> dict:
    body = _plan_body(subject, llm, _ENG_SECTIONS, "ingénieur système", "plan d'ingénierie")
    return _save_plan(subject, body, "ingenierie", out_dir)


def business_plan(subject: str, llm, out_dir=None) -> dict:
    body = _plan_body(subject, llm, _BIZ_SECTIONS, "stratège business", "plan d'affaires réaliste")
    return _save_plan(subject, body, "business", out_dir)
