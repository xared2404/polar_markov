from __future__ import annotations
from pathlib import Path
import hashlib, orjson

def ensure_dir(p: str|Path) -> Path:
    p = Path(p); p.mkdir(parents=True, exist_ok=True); return p

def fid(url: str, text: str) -> str:
    h = hashlib.sha1()
    h.update(url.encode("utf-8"))
    h.update(text[:4000].encode("utf-8", errors="ignore"))
    return h.hexdigest()

def run():
    raw = Path("data/raw")
    out = ensure_dir("data/clean")
    for pole in ["conservative","liberal"]:
        seen = set()
        out_pole = ensure_dir(out / pole)
        for fp in (raw / pole).glob("*.jsonl"):
            rows_out = []
            for line in fp.read_bytes().splitlines():
                r = orjson.loads(line)
                text = (r.get("text") or "").strip()
                if len(text.split()) < 80:
                    continue
                key = fid(r.get("url",""), text)
                if key in seen:
                    continue
                seen.add(key)
                r["text"] = text[:200000]
                rows_out.append(r)
            out_fp = out_pole / fp.name
            with out_fp.open("wb") as f:
                for r in rows_out:
                    f.write(orjson.dumps(r) + b"\n")
            print(f"[OK] {pole} {fp.name}: {len(rows_out)}")
if __name__ == "__main__":
    run()
