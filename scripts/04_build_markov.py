from __future__ import annotations
from pathlib import Path
import yaml, orjson
import numpy as np
from src.markov import build_markov, entropy_rows, loop_strength, kl_divergence

def load_yaml(p: str|Path) -> dict:
    return yaml.safe_load(Path(p).read_text(encoding="utf-8")) or {}

def ensure_dir(p: str|Path) -> Path:
    p = Path(p); p.mkdir(parents=True, exist_ok=True); return p

def read_seqs(fp: Path):
    seqs = []
    for line in fp.read_bytes().splitlines():
        r = orjson.loads(line)
        seqs.append(r["states"])
    return seqs

def run():
    frames_cfg = load_yaml("config/frames.yaml")
    states = list(frames_cfg["frames"].keys())

    feats = Path("data/features")
    out_dir = ensure_dir("data/reports/markov")

    results = {}
    pole_models = {}

    for pole in ["conservative","liberal"]:
        all_seqs = []
        for fp in (feats / pole).glob("*.jsonl"):
            all_seqs.extend(read_seqs(fp))
        mr = build_markov(all_seqs, states)
        pole_models[pole] = mr
        results[pole] = {
            "states": states,
            "counts": mr.counts.tolist(),
            "P": mr.P.tolist(),
            "entropy": entropy_rows(mr.P).tolist(),
            "loop_strength": loop_strength(mr.P).tolist(),
            "n_sequences": len(all_seqs),
        }
        print(f"[OK] pole {pole}: sequences={len(all_seqs)}")

    P = np.array(pole_models["conservative"].P)
    Q = np.array(pole_models["liberal"].P)
    results["divergence"] = {
        "KL_conservative||liberal": kl_divergence(P, Q),
        "KL_liberal||conservative": kl_divergence(Q, P),
    }

    # actor stats simples (basados en secuencias por actor)
    actor_stats = []
    for pole in ["conservative","liberal"]:
        buckets = {}
        for fp in (feats / pole).glob("*.jsonl"):
            for line in fp.read_bytes().splitlines():
                r = orjson.loads(line)
                buckets.setdefault(r.get("actor",""), []).append(r["states"])
        for actor, seqs in buckets.items():
            mr = build_markov(seqs, states)
            H = entropy_rows(mr.P)
            L = loop_strength(mr.P)
            actor_stats.append({
                "pole": pole,
                "actor": actor,
                "n_sequences": len(seqs),
                "mean_entropy": float(np.mean(H)),
                "mean_loop": float(np.mean(L)),
            })
    results["actor_stats"] = sorted(actor_stats, key=lambda x: (x["mean_entropy"], -x["mean_loop"]))

    out_fp = out_dir / "markov_results.json"
    out_fp.write_bytes(orjson.dumps(results, option=orjson.OPT_INDENT_2))
    print(f"[OK] wrote {out_fp}")

if __name__ == "__main__":
    run()
