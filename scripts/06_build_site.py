from __future__ import annotations

from pathlib import Path
import numpy as np
import orjson
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]

SRC_JSON = ROOT / "data" / "reports" / "markov" / "markov_results.json"
SRC_MD   = ROOT / "data" / "reports" / "report.md"

DOCS = ROOT / "docs"
DOCS_DATA = DOCS / "data"
DOCS_ASSETS = DOCS / "assets"

def ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)

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
    if not SRC_JSON.exists():
        raise FileNotFoundError(f"Missing: {SRC_JSON}")
    if not SRC_MD.exists():
        raise FileNotFoundError(f"Missing: {SRC_MD}")

    ensure_dir(DOCS)
    ensure_dir(DOCS_DATA)
    ensure_dir(DOCS_ASSETS)

    (DOCS_DATA / "markov_results.json").write_bytes(SRC_JSON.read_bytes())
    (DOCS_DATA / "report.md").write_text(SRC_MD.read_text(encoding="utf-8"), encoding="utf-8")

    data = orjson.loads(SRC_JSON.read_bytes())
    for pole in ("conservative", "liberal"):
        states = data[pole]["states"]
        P = data[pole]["P"]
        out_img = DOCS_ASSETS / f"heatmap_{pole}.png"
        write_heatmap(P, states, out_img, f"Transition matrix P — {pole}")

    print("[OK] docs/ rebuilt")

if __name__ == "__main__":
    main()
