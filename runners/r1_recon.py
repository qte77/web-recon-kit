"""(1) Recon: render each route, classify the gate type (public / client-side /
server-middleware), capture console errors + a screenshot per route.

Browser tier: run via the borrowed polyfetch venv:
    uv run --directory <polyfetch> python runners/r1_recon.py
"""
from __future__ import annotations

import contextlib
import json
import sys
from pathlib import Path
from typing import TypedDict, cast

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from polyfetch_scrape import render_session  # noqa: E402

from lib.client import load_scope, recon_routes  # noqa: E402


class ReconRow(TypedDict):
    route: str
    doc_http: int | None
    final_url: str
    gate: str
    title: str


def classify(route: str, doc_http: int | None, final_url: str) -> str:
    redirected = final_url.rstrip("/") != route.rstrip("/")
    if not redirected:
        return "public" if doc_http == 200 else f"status-{doc_http}"
    if doc_http == 200:
        return "client-side-gate"   # 200 doc, then JS bounced to /login
    return "server-middleware-gate"  # redirected before content


def main() -> None:
    scope = load_scope()
    base = scope["base_url"]
    routes = recon_routes(scope)
    shots = ROOT / "results" / "screens"
    shots.mkdir(parents=True, exist_ok=True)
    rows: list[ReconRow] = []

    with render_session(base + "/") as session:
        page = session.page
        for route in routes:
            doc_status: dict[str, int | None] = {"code": None}

            def on_resp(
                resp: object, route: str = route, ds: dict[str, int | None] = doc_status,
            ) -> None:
                url = cast(str, getattr(resp, "url", ""))
                if url.rstrip("/") == (base + route).rstrip("/"):
                    ds["code"] = cast(int, getattr(resp, "status", None))

            page.on("response", on_resp)
            with contextlib.suppress(Exception):
                page.goto(base + route, wait_until="domcontentloaded", timeout=25000)
            page.wait_for_timeout(2500)
            final_url = cast(str, page.url).replace(base, "") or "/"
            title = cast(str, page.title() or "")[:80]
            slug = route.strip("/").replace("/", "_") or "root"
            with contextlib.suppress(Exception):
                page.screenshot(path=str(shots / f"{slug}.png"), full_page=False)
            gate = classify(route, doc_status["code"], final_url)
            rows.append({"route": route, "doc_http": doc_status["code"],
                         "final_url": final_url, "gate": gate, "title": title})
            print(f"  {route:<16} doc={doc_status['code']} -> {final_url:<28} [{gate}]")
            page.remove_listener("response", on_resp)

    out = ROOT / "results" / "recon.jsonl"
    out.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    print(f"\n-> {out}  (+ screenshots in results/screens/)")


if __name__ == "__main__":
    main()
