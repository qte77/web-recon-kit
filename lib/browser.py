"""Import guard for the optional browser tier (polyfetch-scrape + patchright)."""
from __future__ import annotations

import sys
from typing import Any

BROWSER_TIER_HINT = (
    "browser tier unavailable: cannot import `polyfetch_scrape`.\n"
    "Install it: uv sync --extra browser && uv run patchright install chromium\n"
    "It is unavailable on musllinux (e.g. Alpine): run on a glibc host, or drive a "
    "system Chromium via CDP (not supported yet — see issue #31)."
)


def require_render_session() -> Any:
    try:
        from polyfetch_scrape import render_session
    except ImportError as exc:
        print(f"{BROWSER_TIER_HINT}\n({exc})", file=sys.stderr)
        raise SystemExit(2) from exc
    return render_session
