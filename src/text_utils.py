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

def _node_text(node) -> str:
    if node is None:
        return ""
    for n in node.css("script,style,noscript,header,footer,nav,aside,form"):
        n.decompose()
    return WS.sub(" ", node.text(separator=" ")).strip()

def extract_visible_text(html: str) -> str:
    tree = HTMLParser(html)

    # Prefer main article containers
    for sel in ["article", "main", "div.article", "div[class*='article']", "div[class*='content']", "section[class*='content']"]:
        nodes = tree.css(sel)
        if nodes:
            t = _node_text(nodes[0])
            if len(t.split()) >= 120:
                return t

    # Fallback: body text
    body = tree.body
    if body:
        return _node_text(body)

    text = tree.text(separator=" ")
    return WS.sub(" ", text).strip()
