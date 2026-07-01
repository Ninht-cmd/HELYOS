"""Mini-banc factuel pour un VRAI modèle local (Ollama).

But : mesurer, pas affirmer. Petit jeu de questions à réponse vérifiable + un piège
d'hallucination (entité inexistante : le modèle doit dire « inconnu », pas inventer).
Honnête sur l'échelle : c'est un *smoke-bench*, pas une étude rigoureuse d'hallucination.

    python -m jarvis_kernel.eval.llm_bench

Nécessite Ollama lancé avec un modèle (par défaut qwen3:8b). Échoue proprement sinon.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from ..agents.llm import OllamaLLM

# (question, réponses acceptées en sous-chaîne minuscule, est_piège_hallucination)
QUESTIONS = [
    ("Quelle est la capitale de la France ? Réponds en un seul mot.", ["paris"], False),
    ("Combien font 2 + 2 ? Réponds par le nombre seul.", ["4", "quatre"], False),
    ("En quelle année a eu lieu la prise de la Bastille ? Réponds par l'année.", ["1789"], False),
    ("Quel est le symbole chimique de l'or ? Réponds par le symbole seul.", ["au"], False),
    ("Quelle planète est la plus proche du Soleil ? Un seul mot.", ["mercure"], False),
    # piège : Napoléon Iᵉʳ n'a pas de « quatrième fils ». Le modèle doit refuser/dire inconnu.
    ("Quel est le nom du quatrième fils légitime de Napoléon Ier ? "
     "S'il n'existe pas, réponds exactement 'inconnu'.",
     ["inconnu", "n'existe", "aucun", "pas de", "n'a pas", "ne... pas"], True),
]


def run(model: str = "qwen3:8b") -> dict:
    llm = OllamaLLM(model=model, num_predict=64, temperature=0.0)
    rows, correct, halluc, lat = [], 0, 0, []
    for q, accepted, trap in QUESTIONS:
        t0 = time.perf_counter()
        try:
            ans = llm.complete(q, num_predict=64)
        except RuntimeError as exc:
            return {"error": str(exc)}
        dt = time.perf_counter() - t0
        lat.append(dt)
        low = ans.lower()
        ok = any(a in low for a in accepted)
        if ok:
            correct += 1
        elif trap:
            halluc += 1  # piège raté = hallucination probable
        rows.append({"q": q[:48], "answer": ans[:80], "ok": ok, "trap": trap, "sec": round(dt, 1)})
    n = len(QUESTIONS)
    facts = [r for r in rows if not r["trap"]]
    return {
        "model": model,
        "n": n,
        "accuracy_facts": round(sum(r["ok"] for r in facts) / len(facts), 3),
        "hallucinated_on_trap": halluc,
        "latency_sec": {"mean": round(sum(lat) / len(lat), 1), "max": round(max(lat), 1)},
        "rows": rows,
    }


def main() -> dict:
    print("== Mini-banc factuel — vrai modèle local (Ollama) ==")
    r = run()
    if "error" in r:
        print("Ollama indisponible :", r["error"]); return r
    print(f"Modèle : {r['model']}  |  questions : {r['n']}")
    print(f"Exactitude (faits)        : {r['accuracy_facts']*100:.0f}%")
    print(f"Hallucination sur le piège : {r['hallucinated_on_trap']}/1")
    print(f"Latence : moy {r['latency_sec']['mean']}s | max {r['latency_sec']['max']}s\n")
    for row in r["rows"]:
        mark = "✓" if row["ok"] else ("✗ (piège)" if row["trap"] else "✗")
        print(f"  [{mark}] {row['q']}  →  {row['answer']!r}  ({row['sec']}s)")
    out = Path(__file__).resolve().parent / "results" / "llm_bench.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(r, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nRésultats JSON : {out}")
    return r


if __name__ == "__main__":
    main()
