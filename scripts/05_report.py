from __future__ import annotations
from pathlib import Path
import orjson
import numpy as np

def mean(x): return float(np.mean(np.array(x, dtype=float))) if x else 0.0

def top_transitions(P, states, k=12):
    P = np.array(P, dtype=float)
    pairs = []
    for i,a in enumerate(states):
        for j,b in enumerate(states):
            pairs.append((P[i,j], a, b))
    pairs.sort(reverse=True, key=lambda x: x[0])
    return pairs[:k]

def run():
    data = orjson.loads(Path("data/reports/markov/markov_results.json").read_bytes())
    states = data["conservative"]["states"]

    lines = []
    lines.append("# Polar Markov Report\n\n")
    div = data.get("divergence", {})
    lines.append("## Divergence (KL)\n")
    lines.append(f"- KL(conservative || liberal): {div.get('KL_conservative||liberal',0.0):.4f}\n")
    lines.append(f"- KL(liberal || conservative): {div.get('KL_liberal||conservative',0.0):.4f}\n\n")

    for pole in ["conservative","liberal"]:
        lines.append(f"## {pole.upper()}\n")
        lines.append(f"- Sequences: {data[pole].get('n_sequences',0)}\n")
        lines.append(f"- Mean entropy: {mean(data[pole].get('entropy',[])):.3f}\n")
        lines.append(f"- Mean loop: {mean(data[pole].get('loop_strength',[])):.3f}\n\n")
        lines.append("### Top transitions\n")
        for p,a,b in top_transitions(data[pole]["P"], states, 12):
            lines.append(f"- {a} → {b}: {p:.3f}\n")
        lines.append("\n")

    lines.append("## Most rigid actors (low mean entropy)\n")
    for r in data.get("actor_stats", [])[:12]:
        lines.append(f"- [{r['pole']}] {r['actor']} | seqs={r['n_sequences']} | mean_entropy={r['mean_entropy']:.3f} | mean_loop={r['mean_loop']:.3f}\n")

    out_fp = Path("data/reports/report.md")
    out_fp.write_text("".join(lines), encoding="utf-8")
    print(f"[OK] wrote {out_fp}")

if __name__ == "__main__":
    run()
