"""(Re)build inventory/api_endpoints.json by mining the live JS bundles.

Static analysis of client code the target ships publicly — no API key needed.
Browser tier: run via the borrowed polyfetch venv:
    uv run --directory <polyfetch> python inventory/build_inventory.py
"""
from __future__ import annotations

import contextlib
import json
import re
import sys
from pathlib import Path
from typing import cast

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from polyfetch_scrape import render_session  # noqa: E402

from lib.client import load_scope, target_host  # noqa: E402
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


def mine(base: str, host: str) -> list[Endpoint]:
    with render_session(base + "/") as session:
        page = session.page
        with contextlib.suppress(Exception):
            page.goto(base + "/", wait_until="networkidle", timeout=30000)
        chunks = cast("dict[str, str]", page.evaluate(_harvest_js(host)) or {})

    api: set[str] = set()
    for text in chunks.values():
        if isinstance(text, str):
            api.update(m.rstrip("/") for m in re.findall(r'["\'`](/api/[A-Za-z0-9_\-./]+)', text))

    endpoints: list[Endpoint] = [{"path": a, "module": module_of(a)} for a in sorted(api)]
    return endpoints


def main() -> None:
    scope = load_scope()
    base = scope["base_url"]
    host = target_host(scope)
    endpoints = mine(base, host)
    out = ROOT / "inventory" / "api_endpoints.json"
    out.write_text(json.dumps(endpoints, indent=2) + "\n")
    print(f"wrote {len(endpoints)} endpoints -> {out}")


if __name__ == "__main__":
    main()
