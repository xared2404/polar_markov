from __future__ import annotations

from pathlib import Path
import json
import numpy as np
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]

SRC_JSON = ROOT / "data" / "reports" / "markov" / "markov_results.json"
SRC_MD   = ROOT / "data" / "reports" / "report.md"

DOCS = ROOT / "docs"
DOCS_DATA = DOCS / "data"
DOCS_ASSETS = DOCS / "assets"

def ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)

def dummy_payload() -> dict:
    # Dummy mínimo (no falla la UI)
    return {
        "conservative": {
            "states": ["S0","S1"],
            "P": [[0.6,0.4],[0.5,0.5]],
            "entropy": [0.673,0.693],
            "loop_strength": [0.6,0.5],
            "n_sequences": 0
        },
        "liberal": {
            "states": ["S0","S1"],
            "P": [[0.55,0.45],[0.4,0.6]],
            "entropy": [0.688,0.673],
            "loop_strength": [0.55,0.6],
            "n_sequences": 0
        },
        "divergence": {
            "KL_conservative||liberal": 0.0,
            "KL_liberal||conservative": 0.0
        },
        "actor_stats": []
    }

def safe_read_json(path: Path) -> dict:
    if not path.exists():
        return dummy_payload()
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return dummy_payload()

def safe_read_md(path: Path) -> str:
    if not path.exists():
        return "# Polar Markov Report\nNo report.md yet. Run the pipeline (scripts/01–05) and push.\n"
    return path.read_text(encoding="utf-8")

def validate_payload(d: dict) -> dict:
    # asegura llaves mínimas
    for pole in ("conservative","liberal"):
        d.setdefault(pole, {})
        d[pole].setdefault("states", ["S0","S1"])
        d[pole].setdefault("P", [[0.5,0.5],[0.5,0.5]])
        d[pole].setdefault("entropy", [0.693,0.693])
        d[pole].setdefault("loop_strength", [0.5,0.5])
        d[pole].setdefault("n_sequences", 0)
    d.setdefault("divergence", {"KL_conservative||liberal": 0.0, "KL_liberal||conservative": 0.0})
    d.setdefault("actor_stats", [])
    return d

def write_heatmap(P: list, states: list[str], out_path: Path, title: str) -> None:
    A = np.array(P, dtype=float)
    fig = plt.figure(figsize=(10, 9), dpi=140)
    ax = fig.add_subplot(111)
    im = ax.imshow(A, aspect="auto")
    ax.set_title(title)
    ax.set_xticks(range(len(states)))
    ax.set_yticks(range(len(states)))
    ax.set_xticklabels(states, rotation=90, fontsize=7)
    ax.set_yticklabels(states, fontsize=7)
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)

def main() -> None:
    ensure_dir(DOCS); ensure_dir(DOCS_DATA); ensure_dir(DOCS_ASSETS)

    data = validate_payload(safe_read_json(SRC_JSON))
    report = safe_read_md(SRC_MD)

    (DOCS_DATA / "markov_results.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
    (DOCS_DATA / "report.md").write_text(report, encoding="utf-8")

    for pole in ("conservative","liberal"):
        states = data[pole]["states"]
        P = data[pole]["P"]
        write_heatmap(P, states, DOCS_ASSETS / f"heatmap_{pole}.png", f"Transition matrix P — {pole}")

    print("[OK] docs/ rebuilt (robust mode)")

if __name__ == "__main__":
    main()
