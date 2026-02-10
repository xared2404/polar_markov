from __future__ import annotations
from pathlib import Path
import yaml, orjson
from src.frame_model import FrameModel

def load_yaml(p: str|Path) -> dict:
    return yaml.safe_load(Path(p).read_text(encoding="utf-8")) or {}

def ensure_dir(p: str|Path) -> Path:
    p = Path(p); p.mkdir(parents=True, exist_ok=True); return p

def run():
    frames_cfg = load_yaml("config/frames.yaml")
    model = FrameModel(frame_lexicon=frames_cfg["frames"])
    clean = Path("data/clean")
    out = ensure_dir("data/features")

    for pole in ["conservative","liberal"]:
        out_pole = ensure_dir(out / pole)
        for fp in (clean / pole).glob("*.jsonl"):
            out_fp = out_pole / fp.name
            n = 0
            with out_fp.open("wb") as f:
                for line in fp.read_bytes().splitlines():
                    r = orjson.loads(line)
                    seq = model.to_state_sequence(r.get("text",""))
                    if len(seq) < 2:
                        continue
                    f.write(orjson.dumps({
                        "actor": r.get("actor",""),
                        "type": r.get("type",""),
                        "url": r.get("url",""),
                        "seed": r.get("seed",""),
                        "states": seq,
                        "n_states": len(seq)
                    }) + b"\n")
                    n += 1
            print(f"[OK] {pole} {fp.name}: {n} sequences")
if __name__ == "__main__":
    run()
