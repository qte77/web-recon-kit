"""(Re)build inventory/api_endpoints.json by mining the live JS bundles.

Static analysis of client code the target ships publicly — no API key needed.
Harvest prefixes: `[inventory].path_prefixes` in scope.toml (default `["/api/"]`);
`[inventory].seed_paths` are appended in both modes.
Browser tier (default): needs the optional `browser` extra (`uv sync --extra browser`
+ `uv run patchright install chromium`), then:
    uv run python inventory/build_inventory.py
API tier (`--no-browser`): fetches the entry HTML and follows code-split JS chunks
with plain throttled GETs (on-host only, capped):
    uv run python inventory/build_inventory.py --no-browser
"""
from __future__ import annotations

import argparse
import asyncio
import contextlib
import json
import sys
from pathlib import Path
from typing import cast

import httpx

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lib.client import (  # noqa: E402
    Throttle,
    get_text,
    inventory_file,
    inventory_prefixes,
    load_scope,
    seed_paths,
    target_host,
)
from lib.inventory import MAX_CHUNK_BYTES, MAX_CHUNKS, crawl, endpoints, harvest_paths  # noqa: E402
from lib.types import Endpoint, EndpointSource, Scope  # noqa: E402


def _harvest_js(base: str) -> str:
    # Reason: exact http(s) host match, as lib.inventory._on_host does for --no-browser —
    # a substring test would let `<host>.evil.test` or `?<host>` URLs through.
    return f"""
async () => {{
  const want = new URL({base!r}).host;
  const urls = new Set();
  document.querySelectorAll('script[src]').forEach(s => urls.add(s.src));
  performance.getEntriesByType('resource').filter(e => e.name.endsWith('.js'))
    .forEach(e => urls.add(e.name));
  const out = {{}};
  for (const u of urls) {{
    let p;
    try {{ p = new URL(u); }} catch (e) {{ continue; }}
    if (!['http:', 'https:'].includes(p.protocol) || p.host !== want) continue;
    try {{ out[u] = await (await fetch(u)).text(); }} catch (e) {{ out[u] = ''; }}
  }}
  return out;
}}
"""


def browser_chunks(base: str) -> dict[str, str]:
    # Reason: imported here so --no-browser runs without the browser extra installed.
    from lib.browser import require_render_session

    render_session = require_render_session()
    with render_session(base + "/") as session:
        page = session.page
        with contextlib.suppress(Exception):
            page.goto(base + "/", wait_until="networkidle", timeout=30000)
        return cast("dict[str, str]", page.evaluate(_harvest_js(base)) or {})


async def static_chunks(scope: Scope, base: str, host: str) -> dict[str, str]:
    thr = Throttle(scope["rate"]["max_concurrency"], scope["rate"]["per_host_delay_ms"])
    async with httpx.AsyncClient(follow_redirects=False) as client:
        entry = await get_text(client, thr, base, "/", MAX_CHUNK_BYTES)
        if entry is None:
            print(f"entry page {base}/ did not return 200 — set base_url to the landing URL")
            return {}

        async def fetch(url: str) -> str | None:
            return await get_text(client, thr, url, "", MAX_CHUNK_BYTES)

        return await crawl(fetch, entry, base + "/", host, MAX_CHUNKS)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--no-browser", action="store_true",
                    help="static crawl of code-split JS chunks over plain GETs (API tier)")
    args = ap.parse_args()

    scope = load_scope()
    base = scope["base_url"]
    host = target_host(scope)
    prefixes = inventory_prefixes(scope)
    source: EndpointSource = "static-crawl" if args.no_browser else "browser"
    chunks = (asyncio.run(static_chunks(scope, base, host)) if args.no_browser
              else browser_chunks(base))

    paths = harvest_paths(chunks, prefixes)
    n_files = sum(1 for t in chunks.values() if isinstance(t, str) and t)
    msg = f"mined {len(paths)} endpoints from {n_files} JS files ({source})"
    print(msg if paths else f"{msg} — check [inventory].path_prefixes in scope.toml")

    eps: list[Endpoint] = endpoints(paths, source, seed_paths(scope))
    out = inventory_file(scope)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(eps, indent=2) + "\n")
    print(f"wrote {len(eps)} endpoints -> {out}")


if __name__ == "__main__":
    main()
