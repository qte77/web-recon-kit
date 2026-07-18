"""(3) BOLA / cross-tenant IDOR. Collect resource IDs as workspace A's owner, then
try to read them as workspace B's owner. A 200 as tenant_b == cross-tenant leak.

Requires identities `owner` and `tenant_b` (2nd workspace). Read-only GETs.
    uv run python runners/r3_bola.py
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import httpx

from lib.client import (
    Throttle,
    bola_collectors,
    get,
    get_json,
    identities,
    load_scope,
    write_jsonl,
)
from lib.types import BolaRow


def extract_ids(data: object, key: str) -> list[str]:
    if not isinstance(data, dict):
        return []
    coll = data.get(key)
    if not isinstance(coll, list):
        return []
    ids: list[str] = []
    for item in coll:
        if isinstance(item, dict) and "id" in item:
            ids.append(str(item["id"]))
    return ids


async def main() -> None:
    scope = load_scope()
    base = scope["base_url"]
    collectors = bola_collectors(scope)
    if not collectors:
        print("SKIP r3_bola: no bola.collectors configured in scope.toml")
        return
    ids = identities(scope)
    owner, tenant_b = ids.get("owner"), ids.get("tenant_b")
    if not owner or not owner["available"] or not tenant_b or not tenant_b["available"]:
        print("SKIP r3_bola: needs both `owner` and `tenant_b` tokens.")
        print("Provision a 2nd tenant and set its API key (identity 'tenant_b' in "
              "scope.toml) in .env, then re-run.")
        return

    thr = Throttle(scope["rate"]["max_concurrency"], scope["rate"]["per_host_delay_ms"])
    rows: list[BolaRow] = []

    async with httpx.AsyncClient(follow_redirects=False) as client:
        for c in collectors:
            kind, list_path, key, template = (
                c["kind"], c["list_path"], c["collection_key"], c["probe_template"],
            )
            status, data = await get_json(client, thr, base, list_path, owner["token"])
            resource_ids = extract_ids(data, key)
            if not resource_ids:
                print(f"  [{kind}] owner list {list_path} -> HTTP {status}, 0 ids (skipping)")
                continue
            for rid in resource_ids:
                probe = template.format(id=rid)
                own = await get(client, thr, base, probe, owner["token"])
                other = await get(client, thr, base, probe, tenant_b["token"])
                leak = other["status"] == 200
                rows.append({"kind": kind, "resource_id": rid, "probe_path": probe,
                             "owner_status": own["status"], "tenant_b_status": other["status"],
                             "leak": leak})
                flag = "  <-- CROSS-TENANT LEAK" if leak else ""
                print(f"  [{kind}] {probe}  owner={own['status']} tenant_b={other['status']}{flag}")

    write_jsonl("bola.jsonl", rows)
    leaks = [r for r in rows if r["leak"]]
    print(f"\n{len(rows)} by-id probes; {len(leaks)} cross-tenant leaks.")
    print("-> results/bola.jsonl")


if __name__ == "__main__":
    asyncio.run(main())
