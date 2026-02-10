from __future__ import annotations
import asyncio
from pathlib import Path
import xml.etree.ElementTree as ET

import yaml, orjson
from src.http_client import HttpClient, FetchConfig
from src.text_utils import extract_links, extract_visible_text

RSS_LINK_LIMIT = 60
RSS_FETCH_LIMIT = 25
PAGE_FETCH_LIMIT = 25
MIN_WORDS = 80

def load_yaml(p: str|Path) -> dict:
    return yaml.safe_load(Path(p).read_text(encoding="utf-8")) or {}

def ensure_dir(p: str|Path) -> Path:
    p = Path(p); p.mkdir(parents=True, exist_ok=True); return p

def looks_like_rss(url: str) -> bool:
    u = url.lower()
    return u.endswith(".xml") or "/feed" in u or "rss" in u

def parse_rss_links(xml_text: str, limit: int = RSS_LINK_LIMIT) -> list[str]:
    try:
        root = ET.fromstring(xml_text)
    except Exception:
        return []

    links = []
    for item in root.findall(".//item"):
        link = item.findtext("link")
        if link:
            links.append(link.strip())
        if len(links) >= limit:
            return links

    ns = "{http://www.w3.org/2005/Atom}"
    for entry in root.findall(f".//{ns}entry"):
        for ln in entry.findall(f"{ns}link"):
            href = ln.attrib.get("href")
            if href:
                links.append(href.strip())
            if len(links) >= limit:
                return links

    return links[:limit]

async def fetch_pages(client: HttpClient, urls: list[str], limit: int) -> list[dict]:
    out, seen = [], set()
    for u in urls:
        if u in seen:
            continue
        seen.add(u)
        out.append(u)
        if len(out) >= limit:
            break

    sem = asyncio.Semaphore(8)

    async def _one(url: str):
        async with sem:
            try:
                html = await client.get_text(url)
                text = extract_visible_text(html)
                wc = len(text.split())
                return {
                    "url": url,
                    "text": text,
                    "word_count": wc,
                    "too_short": wc < MIN_WORDS,
                    "snippet": text[:240]
                }
            except Exception as e:
                return {"url": url, "error": repr(e), "text": "", "word_count": 0, "too_short": True}

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
                name = actor["name"].replace(" ", "_").replace("/", "_")
                all_rows = []
                ok_any = False

                for seed_url in actor.get("urls", []):
                    try:
                        raw = await client.get_text(seed_url)
                        ok_any = True

                        if looks_like_rss(seed_url):
                            links = parse_rss_links(raw, limit=RSS_LINK_LIMIT)
                            all_rows.append({
                                "actor": actor["name"],
                                "type": actor.get("type",""),
                                "seed": seed_url,
                                "url": seed_url,
                                "rss_links": len(links),
                                "mode": "rss"
                            })
                            pages = await fetch_pages(client, links, limit=RSS_FETCH_LIMIT)
                        else:
                            links = extract_links(seed_url, raw)
                            all_rows.append({
                                "actor": actor["name"],
                                "type": actor.get("type",""),
                                "seed": seed_url,
                                "url": seed_url,
                                "text": extract_visible_text(raw),
                                "mode": "html_seed"
                            })
                            pages = await fetch_pages(client, links, limit=PAGE_FETCH_LIMIT)

                        for p in pages:
                            p.update({
                                "actor": actor["name"],
                                "type": actor.get("type",""),
                                "seed": seed_url,
                            })
                        all_rows.extend(pages)

                    except Exception as e:
                        all_rows.append({
                            "actor": actor["name"],
                            "type": actor.get("type",""),
                            "seed": seed_url,
                            "url": seed_url,
                            "error": repr(e),
                            "text": "",
                            "word_count": 0,
                            "too_short": True
                        })
                        print(f"[WARN] {pole}/{actor['name']} seed failed: {seed_url} -> {e.__class__.__name__}")

                out_fp = pole_dir / f"{name}.jsonl"
                with out_fp.open("wb") as f:
                    for r in all_rows:
                        f.write(orjson.dumps(r) + b"\n")

                useful = sum(1 for r in all_rows if (r.get("text") or "").strip() and not r.get("too_short", False))
                short = sum(1 for r in all_rows if r.get("too_short", False))
                if ok_any:
                    print(f"[OK] {pole}/{actor['name']} docs={len(all_rows)} useful={useful} too_short={short}")
                else:
                    print(f"[SKIP] {pole}/{actor['name']} (all seeds failed)")

    finally:
        await client.aclose()

if __name__ == "__main__":
    asyncio.run(main())
