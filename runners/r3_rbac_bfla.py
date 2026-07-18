"""(3) BFLA — function-level authz. Hit admin/RBAC endpoints as a low-role member;
any 200 is a privilege-escalation candidate (member reaching an owner-only surface).

Requires identity `lowrole` (a member token in workspace A). Read-only GETs.
    uv run python runners/r3_rbac_bfla.py
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import httpx

from lib.client import (
    Throttle,
    admin_prefixes,
    get,
    identities,
    load_endpoints,
    load_scope,
    write_jsonl,
)
from lib.types import BflaRow


async def main() -> None:
    scope = load_scope()
    base = scope["base_url"]
    ids = identities(scope)
    owner, low = ids.get("owner"), ids.get("lowrole")
    if not low or not low["available"]:
        print("SKIP r3_rbac_bfla: needs a `lowrole` member token "
              "(identity 'lowrole' in scope.toml).")
        return

    eps = [e for e in load_endpoints() if e["path"].startswith(tuple(admin_prefixes(scope)))]
    thr = Throttle(scope["rate"]["max_concurrency"], scope["rate"]["per_host_delay_ms"])
    owner_tok = owner["token"] if owner and owner["available"] else None
    rows: list[BflaRow] = []

    async with httpx.AsyncClient(follow_redirects=False) as client:
        for ep in eps:
            base_r = await get(client, thr, base, ep["path"], owner_tok)
            low_r = await get(client, thr, base, ep["path"], low["token"])
            noauth_r = await get(client, thr, base, ep["path"], None)
            escalation = low_r["status"] == 200
            rows.append({"path": ep["path"], "owner_status": base_r["status"],
                         "lowrole_status": low_r["status"], "noauth_status": noauth_r["status"],
                         "escalation": escalation})
            flag = "  <-- BFLA: member reached admin surface" if escalation else ""
            print(f"  {ep['path']:<42} owner={base_r['status']} low={low_r['status']} "
                  f"noauth={noauth_r['status']}{flag}")

    write_jsonl("bfla.jsonl", rows)
    esc = [r for r in rows if r["escalation"]]
    print(f"\n{len(eps)} admin/RBAC endpoints; {len(esc)} member-reachable (BFLA candidates).")
    print("-> results/bfla.jsonl")


if __name__ == "__main__":
    asyncio.run(main())
