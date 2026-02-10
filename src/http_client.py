from __future__ import annotations
import asyncio
from dataclasses import dataclass
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential_jitter

@dataclass
class FetchConfig:
    timeout_s: float = 25.0
    max_connections: int = 12
    max_keepalive: int = 6
    rps: float = 1.0
    user_agent: str = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    )

class RateLimiter:
    def __init__(self, rps: float):
        self.min_interval = 1.0 / max(0.1, rps)
        self.lock = asyncio.Lock()
        self.last = 0.0

    async def wait(self):
        async with self.lock:
            now = asyncio.get_event_loop().time()
            dt = now - self.last
            if dt < self.min_interval:
                await asyncio.sleep(self.min_interval - dt)
            self.last = asyncio.get_event_loop().time()

class HttpClient:
    def __init__(self, cfg: FetchConfig):
        self.cfg = cfg
        self.limiter = RateLimiter(cfg.rps)

        limits = httpx.Limits(
            max_connections=cfg.max_connections,
            max_keepalive_connections=cfg.max_keepalive
        )

        headers = {
            "User-Agent": cfg.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }

        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(cfg.timeout_s),
            follow_redirects=True,
            limits=limits,
            headers=headers,
        )

    async def aclose(self):
        await self.client.aclose()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential_jitter(initial=1, max=10))
    async def get_text(self, url: str) -> str:
        await self.limiter.wait()
        r = await self.client.get(url)
        r.raise_for_status()
        return r.text
