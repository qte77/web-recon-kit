"""(2) Cron auth posture. Confirms /api/cron/* are not reachable unauthenticated.

SAFETY: only ever sends GET (no auth). A GET to a POST-only cron handler cannot
execute the job — it returns 401 (auth-first) or 405 (method-gated). We never POST
by default, because a POST could TRIGGER the job. The genuine auth test (POST with
an INVALID cron-secret, expecting rejection before side effects) is left as a
deliberate manual step — see the printed note.
    uv run python runners/r2_cron_auth.py
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import httpx

from lib.client import Throttle, cron_prefix, get, load_endpoints, load_scope, write_jsonl
from lib.types import CronRow, Verdict


def classify(status: int | None) -> Verdict:
    if status in (401, 403):
        return "GATED"
    if status == 405:
        return "METHOD-405"
    return "REVIEW"


async def main() -> None:
    scope = load_scope()
    base = scope["base_url"]
    eps = [e for e in load_endpoints() if e["path"].startswith(cron_prefix(scope))]
    thr = Throttle(4, scope["rate"]["per_host_delay_ms"])
    rows: list[CronRow] = []

    async with httpx.AsyncClient(follow_redirects=False) as client:
        for ep in eps:
            r = await get(client, thr, base, ep["path"], None)
            verdict = classify(r["status"])
            rows.append({"path": ep["path"], "get_noauth_status": r["status"], "verdict": verdict})
            print(f"  {r['status']!s:>4}  {verdict:<12} {ep['path']}")

    write_jsonl("cron_auth.jsonl", rows)
    print(f"\n{len(eps)} cron endpoints probed (GET, no auth).")
    print("405 = route exists but GET not allowed; this does NOT prove the POST "
          "path is authenticated.")
    print("Manual next step: POST with an INVALID cron-secret and confirm 401/403 "
          "BEFORE any side effect.")


if __name__ == "__main__":
    asyncio.run(main())
