from __future__ import annotations
import asyncio
from pathlib import Path
import yaml, orjson
from src.http_client import HttpClient, FetchConfig
from src.text_utils import extract_links, extract_visible_text

def load_yaml(p: str|Path) -> dict:
    return yaml.safe_load(Path(p).read_text(encoding="utf-8")) or {}

def ensure_dir(p: str|Path) -> Path:
    p = Path(p); p.mkdir(parents=True, exist_ok=True); return p

async def fetch_pages(client: HttpClient, urls: list[str], limit: int = 25) -> list[dict]:
    # muestreo simple
    out, seen = [], set()
    for u in urls:
        if u in seen: continue
        seen.add(u); out.append(u)
        if len(out) >= limit: break

    sem = asyncio.Semaphore(8)

    async def _one(url: str):
        async with sem:
            try:
                html = await client.get_text(url)
                return {"url": url, "text": extract_visible_text(html)}
            except Exception as e:
                return {"url": url, "error": repr(e), "text": ""}

    tasks = [_one(u) for u in out]
    res = []
    for fut in asyncio.as_completed(tasks):
        res.append(await fut)
    return res

async def main():
    seeds = load_yaml("config/seeds.yaml")
    out_dir = ensure_dir("data/raw")
    client = HttpClient(FetchConfig())
    try:
        for pole in ["conservative","liberal"]:
            pole_dir = ensure_dir(out_dir / pole)
            for actor in seeds.get(pole, []):
                name = actor["name"].replace(" ", "_")
                all_rows = []
                for seed_url in actor.get("urls", []):
                    html = await client.get_text(seed_url)
                    links = extract_links(seed_url, html)
                    all_rows.append({"actor": actor["name"], "type": actor["type"], "seed": seed_url, "url": seed_url, "text": extract_visible_text(html)})
                    pages = await fetch_pages(client, links, limit=25)
                    for p in pages:
                        p.update({"actor": actor["name"], "type": actor["type"], "seed": seed_url})
                    all_rows.extend(pages)

                out_fp = pole_dir / f"{name}.jsonl"
                with out_fp.open("wb") as f:
                    for r in all_rows:
                        f.write(orjson.dumps(r) + b"\n")
                print(f"[OK] {pole}/{actor['name']} docs={len(all_rows)}")
    finally:
        await client.aclose()

if __name__ == "__main__":
    asyncio.run(main())
