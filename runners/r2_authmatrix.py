"""(2) Auth-posture matrix: every enumerated endpoint x every identity, GET-probed.

Flags unauthenticated 200s on non-public paths (info exposure). Read-only.
    uv run python runners/r2_authmatrix.py
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import httpx

from lib.client import (
    Throttle,
    get,
    identities,
    load_endpoints,
    load_scope,
    public_ok,
    write_jsonl,
)
from lib.types import MatrixRow


async def main() -> None:
    scope = load_scope()
    base = scope["base_url"]
    public = public_ok(scope)
    ids = identities(scope)
    eps = load_endpoints()
    thr = Throttle(scope["rate"]["max_concurrency"], scope["rate"]["per_host_delay_ms"])
    probes: list[tuple[str, str | None]] = [("noauth", None)]
    probes += [(name, idn["token"]) for name, idn in ids.items() if idn["available"]]
    rows: list[MatrixRow] = []

    async with httpx.AsyncClient(follow_redirects=False) as client:
        async def one(path: str, module: str, label: str, token: str | None) -> None:
            r = await get(client, thr, base, path, token)
            rows.append({"path": path, "module": module, "identity": label,
                         "status": r["status"], "content_type": r["content_type"]})

        await asyncio.gather(*[
            one(ep["path"], ep["module"], label, token)
            for ep in eps for (label, token) in probes
        ])

    write_jsonl("authmatrix.jsonl", rows)
    exposed = sorted(
        r["path"] for r in rows
        if r["identity"] == "noauth" and r["status"] == 200 and r["path"] not in public
    )
    print(f"probed {len(eps)} endpoints x {len(probes)} identities = {len(rows)} GETs")
    print(f"identities: {', '.join(label for label, _ in probes)}")
    print(f"\nUNAUTH-200 on non-public paths ({len(exposed)}) — review each:")
    for path in exposed:
        print("  ", path)
    print("\n-> results/authmatrix.jsonl")


if __name__ == "__main__":
    asyncio.run(main())
