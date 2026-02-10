from __future__ import annotations
import re
from urllib.parse import urljoin, urlparse
from selectolax.parser import HTMLParser

WS = re.compile(r"\s+")

def canonical_url(base: str, href: str) -> str | None:
    if not href:
        return None
    href = href.strip()
    if href.startswith(("mailto:", "javascript:", "#")):
        return None
    u = urljoin(base, href)
    p = urlparse(u)
    if p.scheme not in ("http", "https"):
        return None
    return p._replace(fragment="").geturl()

def extract_links(base_url: str, html: str) -> list[str]:
    tree = HTMLParser(html)
    out = []
    for a in tree.css("a"):
        href = a.attributes.get("href")
        u = canonical_url(base_url, href)
        if u:
            out.append(u)
    return out

def extract_visible_text(html: str) -> str:
    tree = HTMLParser(html)
    for n in tree.css("script,style,noscript"):
        n.decompose()
    text = tree.text(separator=" ")
    return WS.sub(" ", text).strip()
