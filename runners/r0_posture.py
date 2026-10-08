"""(0) Passive host posture per domain: DNS (SPF / DMARC / null MX / CAA / DNSSEC) and
HTTP security headers (HSTS / CSP / nosniff / Referrer-Policy / Permissions-Policy,
http -> https redirect).

SAFETY: passive only. DNS answers come from public DNS-over-HTTPS resolvers
(`[posture].doh_urls`, default Cloudflare then Google) — the resolver operators see the
domain names queried. The target gets exactly two throttled GETs per domain
(`http://<d>/`, `https://<d>/`, redirects not followed). No zone transfers, no scans.
Domains: `[posture].domains`, default the base_url host minus a leading `www.`.
    uv run python runners/r0_posture.py
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import httpx

from lib.client import Throttle, get, get_headers, load_scope, write_jsonl
from lib.posture import QUERIES, check_dns, check_headers, doh_query, settings
from lib.types import DohResponse, PostureFinding


async def main() -> None:
    scope = load_scope()
    cfg = settings(scope)
    thr = Throttle(scope["rate"]["max_concurrency"], scope["rate"]["per_host_delay_ms"])
    rows: list[PostureFinding] = []

    async with httpx.AsyncClient(follow_redirects=False) as client:
        for domain in cfg["domains"]:
            q: dict[str, DohResponse | None] = {}
            for label, (template, rtype) in QUERIES.items():
                name = template.format(d=domain)
                q[label] = await doh_query(client, thr, cfg["doh_urls"], name, rtype)
            http = await get(client, thr, f"http://{domain}", "/")
            status, headers = await get_headers(client, thr, f"https://{domain}", "/")
            for f in check_dns(domain, cfg, q) + check_headers(domain, cfg, status, headers, http):
                rows.append(f)
                mark = "ok  " if f["ok"] else f"FAIL {f['severity']:<6}"
                print(f"  {domain:<28} {mark} {f['check']:<14} {f['detail']}")

    out = write_jsonl(scope, "posture.jsonl", rows)
    failing = [r for r in rows if not r["ok"]]
    print(f"\n{len(cfg['domains'])} domain(s); {len(failing)} failing posture checks.")
    print(f"-> {out}")


if __name__ == "__main__":
    asyncio.run(main())
