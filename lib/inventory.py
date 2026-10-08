"""Pure JS-bundle path-mining logic for inventory/build_inventory.py (mypy --strict clean)."""

from __future__ import annotations

import re
from collections import deque
from collections.abc import Awaitable, Callable, Iterable, Mapping, Sequence
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

from lib.types import Endpoint, EndpointSource

_PATH_CHARS = r"[A-Za-z0-9_\-./]+"

# Static-crawl bounds (politeness + memory): chunks fetched per run, bytes read per chunk.
MAX_CHUNKS = 100
MAX_CHUNK_BYTES = 2_000_000

# `import("./x.js")`, `from"../y.js"` (relative to the importing chunk) and absolute
# `"/assets/z.js"` literals — the forms bundlers emit for code-split chunks.
_CHUNK_REF = re.compile(
    r"""(?:import\s*\(\s*|from\s*)["'`]([^"'`\s]+\.m?js)["'`]"""
    r"""|["'`](/[A-Za-z0-9_\-./]+\.m?js)["'`]"""
)


def path_pattern(prefixes: Sequence[str]) -> re.Pattern[str]:
    alts = "|".join(re.escape(p) for p in prefixes)
    return re.compile(rf"""["'`]((?:{alts}){_PATH_CHARS})""")


def harvest_paths(chunks: Mapping[str, object], prefixes: Sequence[str]) -> list[str]:
    """Mine literal path strings under any of `prefixes` from JS bundle text."""
    if not prefixes:
        return []
    pattern = path_pattern(prefixes)
    return sorted(
        {
            m.rstrip("/")
            for text in chunks.values()
            if isinstance(text, str)
            for m in pattern.findall(text)
        }
    )


def _on_host(urls: Iterable[str], host: str) -> list[str]:
    # Reason: exact scheme + netloc match. A substring test (`host in url`, as the browser
    # path's in-page filter uses) would let `https://<host>.evil.test/` or `?<host>` through,
    # and here the harness itself issues the GET — the crawl must never leave scope.
    return list(
        dict.fromkeys(
            u for u in urls if (p := urlparse(u)).scheme in ("http", "https") and p.netloc == host
        )
    )


class _ScriptParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.refs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = dict(attrs)
        if tag == "script" and a.get("src"):
            self.refs.append(a["src"] or "")
        elif tag == "link" and (a.get("rel") or "").lower() == "modulepreload" and a.get("href"):
            self.refs.append(a["href"] or "")


def script_urls(html: str, page_url: str, host: str) -> list[str]:
    """On-host `<script src>` + `<link rel=modulepreload>` URLs, resolved, deduped."""
    parser = _ScriptParser()
    parser.feed(html)
    return _on_host((urljoin(page_url, r) for r in parser.refs), host)


def chunk_urls(js: str, chunk_url: str, host: str) -> list[str]:
    """On-host chunk URLs a JS chunk references, resolved against that chunk's URL."""
    refs = (rel or absolute for rel, absolute in _CHUNK_REF.findall(js))
    return _on_host((urljoin(chunk_url, r) for r in refs), host)


async def crawl(
    fetch: Callable[[str], Awaitable[str | None]],
    entry_html: str,
    page_url: str,
    host: str,
    max_chunks: int = MAX_CHUNKS,
) -> dict[str, str]:
    """Breadth-first walk of on-host JS chunks from the entry page. Each URL is fetched
    at most once; at most `max_chunks` fetches; a failed fetch is kept as ''."""
    queue = deque(script_urls(entry_html, page_url, host))
    seen = set(queue)
    chunks: dict[str, str] = {}
    while queue and len(chunks) < max_chunks:
        url = queue.popleft()
        text = await fetch(url) or ""
        chunks[url] = text
        for nxt in chunk_urls(text, url, host):
            if nxt not in seen:
                seen.add(nxt)
                queue.append(nxt)
    return chunks


def module_of(path: str) -> str:
    parts = path.split("/")
    return parts[2] if len(parts) > 2 else ""


def endpoints(paths: Sequence[str], source: EndpointSource, seeds: Sequence[str]) -> list[Endpoint]:
    """Mined paths tagged with their source, then any seed paths not already mined."""
    mined = set(paths)
    out: list[Endpoint] = [{"path": p, "module": module_of(p), "source": source} for p in paths]
    out += [
        {"path": s, "module": module_of(s), "source": "seed"}
        for s in dict.fromkeys(seeds)
        if s not in mined
    ]
    return out
