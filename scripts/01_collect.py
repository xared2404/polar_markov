from __future__ import annotations
import asyncio
from pathlib import Path
import xml.etree.ElementTree as ET

import httpx
import yaml, orjson

from src.http_client import HttpClient, FetchConfig
from src.text_utils import extract_links, extract_visible_text

RSS_LINK_LIMIT = 80
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

def is_probably_xml(text: str) -> bool:
    t = (text or "").lstrip()[:200].lower()
    return t.startswith("<?xml") or t.startswith("<rss") or t.startswith("<feed")

def localname(tag: str) -> str:
    return tag.split("}", 1)[-1] if "}" in tag else tag

def parse_rss_links(xml_text: str, limit: int = RSS_LINK_LIMIT) -> list[str]:
    if not is_probably_xml(xml_text):
        return []
    try:
        root = ET.fromstring(xml_text)
    except Exception:
        return []

    links: list[str] = []

    # RSS <item> ... (namespace-agnostic)
    items = [e for e in root.iter() if localname(str(e.tag)) == "item"]
    for item in items:
        link = ""
        guid = ""

        for child in list(item):
            ln = localname(str(child.tag))
            if ln == "link" and (child.text or "").strip():
                link = child.text.strip()
            elif ln == "guid" and (child.text or "").strip():
                guid = child.text.strip()

        if not link and guid.startswith("http"):
            link = guid

        if link.startswith("http"):
            links.append(link)
        if len(links) >= limit:
            return links[:limit]

    # Atom <entry><link href="..."> (namespace-agnostic)
    entries = [e for e in root.iter() if localname(str(e.tag)) == "entry"]
    for entry in entries:
        for child in list(entry):
            if localname(str(child.tag)) == "link":
                href = (child.attrib.get("href") or "").strip()
                rel = (child.attrib.get("rel") or "").strip()
                if href.startswith("http") and (rel in ("", "alternate")):
                    links.append(href)
                    if len(links) >= limit:
                        return links[:limit]

    return links[:limit]

def fetch_rss_sync(url: str) -> str:
    """
    Fetch RSS using headers similar to scripts/00_probe_feed.py
    (This avoids async-client behaviors that may trigger different responses.)
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123 Safari/537.36",
        "Accept": "application/rss+xml, application/atom+xml, application/xml;q=0.9, text/xml;q=0.8, */*;q=0.5",
        "Accept-Language": "en-US,en;q=0.9",
    }
    with httpx.Client(headers=headers, follow_redirects=True, timeout=20) as c:
        r = c.get(url)
        r.raise_for_status()
        return r.text

async def fetch_rss(url: str) -> str:
    return await asyncio.to_thread(fetch_rss_sync, url)

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
        for pole in ["conservative", "liberal"]:
            pole_dir = ensure_dir(out_dir / pole)
            for actor in seeds.get(pole, []):
                name = actor["name"].replace(" ", "_").replace("/", "_")
                all_rows = []
                ok_any = False

                rss_links_n = 0
                pages_fetched = 0
                pages_error = 0

                for seed_url in actor.get("urls", []):
                    try:
                        # IMPORTANT: RSS fetch uses probe-like sync client
                        if looks_like_rss(seed_url):
                            raw = await fetch_rss(seed_url)
                        else:
                            raw = await client.get_text(seed_url)

                        ok_any = True

                        if looks_like_rss(seed_url):
                            links = parse_rss_links(raw, limit=RSS_LINK_LIMIT)
                            rss_links_n += len(links)

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

                        pages_fetched += len(pages)
                        pages_error += sum(1 for p in pages if "error" in p)

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

                useful = sum(
                    1 for r in all_rows
                    if (r.get("text") or "").strip() and not r.get("too_short", False)
                )
                short = sum(1 for r in all_rows if r.get("too_short", False))

                if ok_any:
                    extra = f" rss_links={rss_links_n} pages={pages_fetched} page_errors={pages_error}"
                    print(f"[OK] {pole}/{actor['name']} docs={len(all_rows)} useful={useful} too_short={short}{extra}")
                else:
                    print(f"[SKIP] {pole}/{actor['name']} (all seeds failed)")

    finally:
        await client.aclose()

if __name__ == "__main__":
    asyncio.run(main())
