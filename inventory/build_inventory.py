"""(Re)build inventory/api_endpoints.json by mining the live JS bundles.

Static analysis of client code the target ships publicly — no API key needed.
Harvest prefixes: `[inventory].path_prefixes` in scope.toml (default `["/api/"]`).
Browser tier: needs the optional `browser` extra (`uv sync --extra browser`
+ `uv run patchright install chromium`), then:
    uv run python inventory/build_inventory.py
"""
from __future__ import annotations

import contextlib
import json
import sys
from pathlib import Path
from typing import cast

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from polyfetch_scrape import render_session  # noqa: E402

from lib.client import inventory_prefixes, load_scope, target_host  # noqa: E402
from lib.inventory import harvest_paths  # noqa: E402
from lib.types import Endpoint  # noqa: E402


def _harvest_js(host: str) -> str:
    return f"""
async () => {{
  const urls = new Set();
  document.querySelectorAll('script[src]').forEach(s => urls.add(s.src));
  performance.getEntriesByType('resource').filter(e => e.name.endsWith('.js'))
    .forEach(e => urls.add(e.name));
  const out = {{}};
  for (const u of urls) {{
    if (!u.includes({host!r})) continue;
    try {{ out[u] = await (await fetch(u)).text(); }} catch (e) {{ out[u] = ''; }}
  }}
  return out;
}}
"""


def module_of(path: str) -> str:
    parts = path.split("/")
    return parts[2] if len(parts) > 2 else ""


def mine(base: str, host: str, prefixes: tuple[str, ...]) -> list[Endpoint]:
    with render_session(base + "/") as session:
        page = session.page
        with contextlib.suppress(Exception):
            page.goto(base + "/", wait_until="networkidle", timeout=30000)
        chunks = cast("dict[str, str]", page.evaluate(_harvest_js(host)) or {})

    paths = harvest_paths(chunks, prefixes)
    n_files = sum(1 for t in chunks.values() if isinstance(t, str) and t)
    msg = f"mined {len(paths)} endpoints from {n_files} JS files"
    print(msg if paths else f"{msg} — check [inventory].path_prefixes in scope.toml")

    return [{"path": p, "module": module_of(p)} for p in paths]


def main() -> None:
    scope = load_scope()
    base = scope["base_url"]
    host = target_host(scope)
    prefixes = inventory_prefixes(scope)
    endpoints = mine(base, host, prefixes)
    out = ROOT / "inventory" / "api_endpoints.json"
    out.write_text(json.dumps(endpoints, indent=2) + "\n")
    print(f"wrote {len(endpoints)} endpoints -> {out}")


if __name__ == "__main__":
    main()
