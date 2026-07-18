"""Aggregate results/*.jsonl into results/report.md. Pure stdlib, strictly typed.
    uv run python report.py
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import cast

ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results"


def read(name: str) -> list[dict[str, object]]:
    path = RESULTS / name
    if not path.exists():
        return []
    return [cast("dict[str, object]", json.loads(line))
            for line in path.read_text().splitlines() if line.strip()]


def section_authmatrix(md: list[str]) -> None:
    rows = read("authmatrix.jsonl")
    if not rows:
        return
    md.append("## Auth matrix\n")
    by_status: Counter[str] = Counter(f"{r['identity']}:{r['status']}" for r in rows)
    md.append(f"- {len(rows)} probes across identities.")
    exposed = sorted(
        {str(r["path"]) for r in rows if r["identity"] == "noauth" and r["status"] == 200}
    )
    md.append(f"- **Unauth-200 (non-public review): {len(exposed)}**")
    for p in exposed:
        md.append(f"  - `{p}`")
    md.append("\n<details><summary>status tallies</summary>\n")
    for key, n in sorted(by_status.items()):
        md.append(f"- `{key}`: {n}")
    md.append("</details>\n")


def section_cron(md: list[str]) -> None:
    rows = read("cron_auth.jsonl")
    if not rows:
        return
    md.append("## Cron auth\n")
    review = [r for r in rows if r["verdict"] == "REVIEW"]
    md.append(f"- {len(rows)} cron endpoints; **{len(review)} REVIEW (not clearly gated)**.")
    for r in review:
        md.append(f"  - `{r['path']}` (GET no-auth → {r['get_noauth_status']})")


def section_bola(md: list[str]) -> None:
    rows = read("bola.jsonl")
    if not rows:
        return
    leaks = [r for r in rows if r["leak"]]
    md.append("## BOLA (cross-tenant)\n")
    md.append(f"- {len(rows)} by-id probes; **{len(leaks)} cross-tenant leaks**.")
    for r in leaks:
        md.append(f"  - `{r['probe_path']}` readable by tenant_b (status {r['tenant_b_status']})")


def section_bfla(md: list[str]) -> None:
    rows = read("bfla.jsonl")
    if not rows:
        return
    esc = [r for r in rows if r["escalation"]]
    md.append("## BFLA (function-level)\n")
    md.append(f"- {len(rows)} admin/RBAC endpoints; **{len(esc)} member-reachable**.")
    for r in esc:
        md.append(f"  - `{r['path']}` reachable by low-role member (status {r['lowrole_status']})")


def section_recon(md: list[str]) -> None:
    rows = read("recon.jsonl")
    if not rows:
        return
    md.append("## Recon / gate taxonomy\n")
    for r in rows:
        md.append(f"- `{r['route']}` → {r['gate']} (doc {r['doc_http']}, final `{r['final_url']}`)")


def main() -> None:
    md: list[str] = ["# web-recon-kit — aggregated results\n"]
    for fn in (section_recon, section_authmatrix, section_cron, section_bola, section_bfla):
        fn(md)
        md.append("")
    out = RESULTS / "report.md"
    out.parent.mkdir(exist_ok=True)
    out.write_text("\n".join(md) + "\n")
    print(f"-> {out}")


if __name__ == "__main__":
    main()
