from __future__ import annotations
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
SRC_JSON = ROOT / "data" / "reports" / "markov" / "markov_results.json"
SRC_MD   = ROOT / "data" / "reports" / "report.md"

DST_DIR  = ROOT / "docs" / "data"
DST_JSON = DST_DIR / "markov_results.json"
DST_MD   = DST_DIR / "report.md"

def ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)

def main():
    ensure_dir(DST_DIR)

    if not SRC_JSON.exists():
        raise SystemExit(f"[ERR] missing: {SRC_JSON} (run scripts/04_build_markov.py first)")
    if not SRC_MD.exists():
        raise SystemExit(f"[ERR] missing: {SRC_MD} (run scripts/05_report.py first)")

    shutil.copy2(SRC_JSON, DST_JSON)
    shutil.copy2(SRC_MD, DST_MD)

    print("[OK] docs/ rebuilt (copy-only)")
    print(f"     -> {DST_JSON}")
    print(f"     -> {DST_MD}")

if __name__ == "__main__":
    main()
