from __future__ import annotations
from pathlib import Path
import yaml, orjson
import numpy as np
from src.markov import build_markov, entropy_rows, loop_strength, kl_divergence

MIN_ACTOR_SEQS = 3  # umbral para guardar Markov por actor (evita ruido)

def load_yaml(p: str|Path) -> dict:
    return yaml.safe_load(Path(p).read_text(encoding="utf-8")) or {}

def ensure_dir(p: str|Path) -> Path:
    p = Path(p); p.mkdir(parents=True, exist_ok=True); return p

def read_rows(fp: Path):
    for line in fp.read_bytes().splitlines():
        yield orjson.loads(line)

def safe_key(s: str) -> str:
    return (
        s.strip()
        .replace(" ", "_")
        .replace("/", "_")
        .replace("(", "")
        .replace(")", "")
        .replace("__", "_")
    )

def run():
    frames_cfg = load_yaml("config/frames.yaml")
    states = list(frames_cfg["frames"].keys())

    feats = Path("data/features")
    out_dir = ensure_dir("data/reports/markov")

    results: dict = {}
    pole_models = {}

    # ---- Pole-level Markov
    for pole in ["conservative","liberal"]:
        all_seqs = []
        for fp in (feats / pole).glob("*.jsonl"):
            for r in read_rows(fp):
                all_seqs.append(r["states"])

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

    # ---- Actor-level Markov (NEW)
    actors_out = {}
    actor_stats = []

    for pole in ["conservative","liberal"]:
        buckets: dict[str, list[list[str]]] = {}
        for fp in (feats / pole).glob("*.jsonl"):
            for r in read_rows(fp):
                actor = r.get("actor","").strip() or "Unknown"
                buckets.setdefault(actor, []).append(r["states"])

        for actor, seqs in buckets.items():
            n = len(seqs)

            mr = build_markov(seqs, states)
            H = entropy_rows(mr.P)
            L = loop_strength(mr.P)

            actor_stats.append({
                "pole": pole,
                "actor": actor,
                "n_sequences": n,
                "mean_entropy": float(np.mean(H)),
                "mean_loop": float(np.mean(L)),
            })

            # guardamos solo si hay suficiente soporte empírico
            if n >= MIN_ACTOR_SEQS:
                k = f"{pole}::{safe_key(actor)}"
                actors_out[k] = {
                    "pole": pole,
                    "actor": actor,
                    "n_sequences": n,
                    "states": states,
                    "counts": mr.counts.tolist(),
                    "P": mr.P.tolist(),
                    "entropy": H.tolist(),
                    "loop_strength": L.tolist(),
                }

    results["actors_min_seqs"] = MIN_ACTOR_SEQS
    results["actors"] = actors_out

    # actor_stats global: ordena por menor entropía (más “rígido”)
    results["actor_stats"] = sorted(
        actor_stats,
        key=lambda x: (x["mean_entropy"], -x["mean_loop"], -x["n_sequences"])
    )

    out_fp = out_dir / "markov_results.json"
    out_fp.write_bytes(orjson.dumps(results, option=orjson.OPT_INDENT_2))
    print(f"[OK] wrote {out_fp}")
    print(f"[OK] actor matrices saved: {len(actors_out)} (min_seqs={MIN_ACTOR_SEQS})")

if __name__ == "__main__":
    run()
