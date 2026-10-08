# Arc 0002 — close arc 0001, clear the Dependabot queue, ship #41 → (#56 ∥ #55)

**Start here — this file is the complete context for this arc.** Read only this file; the
exploration behind it is done (see "Source map"). Do not re-map the codebase.

**Status (2026-10-08):** planned, owner-approved scope; only row 3 done (this doc, PR #57).
Start with row 1. Arc 0001 (`docs/plans/0001-housekeeping-and-issue-backlog.md`) is
CLOSED in the same PR that adds this file; its leftovers are rows 8 and D1–D4 below.

**Next, in order:** (1) re-verify live state (drift happened after every gap: open PRs
#52/#53/#54, alert #8, issues #41/#55/#56, `git status`/`git branch` clean `main`);
(2) Lane 0 rows 1–4 serially from the coordinator; (3) row 5 (#41) — it is the shared
foundation; (4) then Lane A (#56, row 6) **∥** Lane B (#55, rows 7a→7b) in parallel worktrees;
(5) owner sitting for rows 8–9; (6) arc close-out audit.

**Unattended run contract (owner-approved 2026-10-08):** execute rows 1 → 7b end to end
with no check-ins. Each row: branch (`chore/…`, `fix/…`, `feat/…`), RED → GREEN → docs →
fragment → strike own row (PR number via a follow-up commit on the same branch) → full
gate → PR → watch all checks → merge → `git switch main && git fetch --prune && git merge
--ff-only origin/main` → one-line progress note (shipped · next · % · blocked).
- **Decide-by-default on drift:** a row already done by someone else → verify, strike it with
  the actual PR/evidence, continue. A new Dependabot PR → merge it like rows 1–2 if green.
  New issues → add a deferred row, don't implement.
- **Stop and report only on:** a gate that would need relaxing; a check failing for a
  reason not caused by the slice that persists after one update-branch; a merge blocked
  by a rule even with `--admin`; any change that would weaken an AGENTS.md guardrail
  (GET/OPTIONS only, throttling, nothing target-specific committed); an ambiguity not
  covered by the slice spec.
- **At arc end:** run Verification, strike the arc status to "rows 1–7b done", update
  auto-memory `arc-0001-plan-status.md` to point at this file, report rows 8–9 as the owner
  sitting.

**The loop (parallel subagents in worktrees):** after row 5 merges, the coordinator launches
one fresh `general-purpose` agent per lane with `isolation: "worktree"`, each briefed to
read this file. RED/GREEN/docs run fully in parallel; the coordinator holds a **single
merge token** (main requires up-to-date branches, so only one lane rebases+merges at a time).
Conflict recipe for shared files (lib/client.py, lib/types.py, Makefile, docs, this plan's
table): different functions/classes/targets/sections → keep both sides.
**Precondition — currently NOT met:** `~/.claude/hooks/rtk-rewrite.sh` rewrites `git …` to
`rtk git …` and Claude Code's worktree-isolation guard then refuses every git command
(re-verified unpatched 2026-10-08). Fix = owner patches the hook to skip `^\s*git(\s|$)`
(the auto-mode classifier blocks the agent from editing it). Until then: the coordinator
runs each lane itself, serially — proven across arc 0001.

**Owner gates (one sitting, Phase B):** rows 8 + 9 (real-target e2e); the hook patch above if
parallel lanes are wanted. Commands pre-staged in "Access checklist".

**Key commands:** every `gh`/`git push`: `env -u GH_TOKEN -u GITHUB_TOKEN …`. Gate before
push: `uv run ruff check . && uv run mypy && uv run pytest --cov && uv run pip-audit`, plus
`uv run ruff format --check <changed .py>`, `markdownlint` (ignore MD013 — local config
mismatch) + `lychee --offline` on changed .md, `actionlint`/`zizmor --offline` if a workflow
changes. Merge agent PRs: `gh pr checks N --watch` until all green, then `gh pr merge N
--admin --squash --delete-branch`; Dependabot PRs too (owner, 2026-10-08: always `--admin
--squash`, never modify rulesets; `--admin` still needs CodeFactor reported). BEHIND →
`gh api repos/qte77/web-recon-kit/pulls/N/update-branch -X PUT`.

**Watch-outs:** Bash denies cat/grep/head/tail/find/ls → Read tool, `rtk grep`, `git grep`.
Strict TDD (RED run first), tests only for `lib/` logic; runners = dry-run/e2e proof. One
`changelog.d/` fragment per slice (`uv run scriv create --add`). Strike the row in the same
PR. `polyfetch_scrape` is not installed in this sandbox (browser path can't run here). The
owner chose to keep this plan as specced after a KISS/DRY/YAGNI review (2026-10-08).

## Context

Arc 0001 shipped rows 1–15 by 2026-09-18. Re-verified 2026-10-08: Dependabot opened #52
(`python-deps`), #53 (`github-actions`), #54 (`python-deps-security`) — correctly grouped +
labeled, closing 0001's row 7; all MERGEABLE/CLEAN, green. Alert #8 (urllib3,
CVE-2026-97688, medium) is fixed by #54. #41 got real evidence (4-host run needed manual
backup/restore of `inventory/`+`results/`). New qte77 issues #55, #56. `git check-ignore`:
`scope.acme.toml` NOT ignored (README.md:96 recommends it) and nested
`*/inventory/api_endpoints.json` NOT ignored. Owner decisions: close 0001 in place with a
CLOSED banner; go all the way; #41 = scope-file dir + optional `[output].dir`; #55 DoH =
Cloudflare → Google, overridable list; keep #56/#55 as specced; full plan doc.

## Lane map

| Lane | Rows (in order) | Files owned |
| --- | --- | --- |
| 0 coordinator | 1 #54 → 2 #52, #53 → 3 docs(plan) → 4 .gitignore → 5 #41 | uv.lock, .github/workflows/*, docs/plans/*, docs/roadmap.md, .gitignore, lib/client.py (paths), runners/*, report.py, inventory/build_inventory.py (output path) |
| A (after 5) | 6 #56 | inventory/build_inventory.py, lib/inventory.py, lib/client.py `get_text`, lib/types.py `Endpoint`, tests/test_inventory.py, Makefile `inventory-static`, scope.example.toml `[inventory]` |
| B (after 5) | 7a #55 DNS → 7b #55 headers+report | runners/r0_posture.py (new), lib/posture.py (new), lib/client.py `get_headers`, lib/types.py posture types, tests/test_posture.py, report.py, Makefile `posture`, scope.example.toml `[posture]` |

## Remaining-work table (the ONE list; gate = agent / owner / data)

| # | Item | Lane | Gate | Done-when |
| --- | --- | --- | --- | --- |
| 1 | ~~Merge #54 (urllib3, alert #8)~~ | 0 | agent | DONE — #54 merged 2026-10-08 08:25; 0 open alerts |
| 2 | ~~Merge #52, #53~~ | 0 | agent | DONE — #52 closed by Dependabot, superseded by #58 (merged); #53 merged |
| 3 | Close 0001 in place (CLOSED banner, row 7 DONE w/ #52–#54) + add this doc + roadmap link | 0 | agent | DONE — [PR #57](https://github.com/qte77/web-recon-kit/pull/57) |
| 4 | ~~`.gitignore`~~ ([PR #59](https://github.com/qte77/web-recon-kit/pull/59)): `scope.*.toml` + `!scope.example.toml`, `**/inventory/api_endpoints.json` | 0 | agent | `git check-ignore` ignores `scope.acme.toml`, `targets/x/scope.toml`, `targets/x/inventory/api_endpoints.json`, `targets/x/results/a.jsonl`; NOT `scope.example.toml` |
| 5 | ~~#41 per-scope output dir~~ ([PR #60](https://github.com/qte77/web-recon-kit/pull/60)) | 0 | agent | tests + dry run (two scope dirs → separate outputs, root untouched); `Closes #41` |
| 6 | ~~#56 `--no-browser` static crawl~~ (PR #TBD) | A | agent | non-empty inventory from code-split fixture, chunk cap tested; `Closes #56` |
| 7a | #55 DoH client + DNS checks | B | agent | fixture tests incl. fallback + split TXT; `Refs #55` |
| 7b | #55 headers + report section + `make posture` | B | agent | fixture tests; report section; `Closes #55` |
| 8 | (from 0001 row 16) browser-tier e2e of `console_errors`/`cookie_findings` | — | owner | real-target rows show both fields |
| 9 | Real-target e2e of #41/#56/#55 | — | owner | outputs per target dir; non-empty static inventory; `posture.jsonl` |
| D1 | #21-3 network log | — | deferred | upstream polyfetch-scrape#182 (open) |
| D2 | #17 pagination / multi-segment / spec discovery (+ #56 OpenAPI seed) | — | deferred | YAGNI |
| D3 | #31 CDP fallback | — | deferred | YAGNI |
| D4 | #25 automated release | — | deferred | upstream qte77/.github#38 (open) |
| D5 | DoH wire format (RFC 8484, e.g. Quad9) | — | deferred | YAGNI; needs a binary DNS parser |

## Slice specs (HOW — the table above is WHAT)

### Row 4 · .gitignore
Add `scope.*.toml`, `!scope.example.toml`, `**/inventory/api_endpoints.json`. No test
(config); proof = the `git check-ignore` matrix. Update `docs/architecture.md:78`
safety-invariant bullet. Fragment (Security).

### Row 5 · #41 — output dir = scope-file dir, `[output].dir` overrides
`output_dir(scope)` = `[output].dir` resolved against the scope file's directory if set,
else the scope file's directory; `scope_path()` resolved first (it returns the raw override,
`Path("scope.acme.toml").parent == "."`). Default `./scope.toml` → repo root → no behavior
change. Documented layout: `targets/<name>/scope.toml` → `targets/<name>/{results,inventory}/`.
- RED `tests/test_client.py` (style of the RECON_SCOPE tests :179-233, `monkeypatch` +
  `tmp_path`): default → `ROOT`; `RECON_SCOPE=tmp/a/scope.toml` → `tmp/a`; `[output].dir
  = "out/acme"` → `tmp/a/out/acme`; absolute dir as-is; `write_jsonl` creates parents
  (today `mkdir(exist_ok=True)` lacks `parents=True`); `load_endpoints` reads
  `<out>/inventory/api_endpoints.json`.
- GREEN: `lib/types.py` `OutputCfg(TypedDict): dir: NotRequired[str]`, `Scope.output`.
  `lib/client.py`: `output_dir`, `results_dir`, `inventory_file`; `load_endpoints(scope)`,
  `write_jsonl(scope, name, rows)`; update callers. `r1_recon.py`, `build_inventory.py`
  use the helpers (local `ROOT` kept only for `sys.path.insert`). `report.py`:
  `results_dir(load_scope())` in `try/except FileNotFoundError` → fallback `ROOT/results`;
  fix its "Pure stdlib" docstring.
- Docs: architecture.md Config-model `[output] dir` row + CLI/env `RECON_SCOPE` row
  (also selects output location); README §Run: replace the `scope.acme.toml` example
  (README.md:96) with the `targets/<name>/` layout + `[output].dir` for siblings;
  scope.example.toml commented `[output]`; note Makefile `clean` is root-only.
  Fragment (Added).

### Row 6 · #56 — `build_inventory.py --no-browser`
- Prereq: move `render_session = require_render_session()` from module level into the
  browser path of `mine()` (else `--no-browser` exits 2 at import). Re-verify
  `.github/workflows/browser-tier.yml` still imports `polyfetch_scrape` directly first.
- RED `tests/test_inventory.py` (pure fixtures): `script_urls(html, page_url, host)` via
  stdlib `html.parser` (`<script src>`, `<link rel=modulepreload>`); `chunk_urls(js,
  chunk_url, host)` — `import("./x.js")` resolved against the fetching chunk's URL, plus
  `"/assets/…js"` literals; host filter mirrors `_harvest_js` (`host in url`);
  `crawl(fetch, entry_html, page_url, host, max_chunks)` reaches a 3-level leaf, stops at
  cap, no re-fetch, never leaves host. `harvest_paths` unchanged.
- GREEN: `lib/client.py` `get_text(client, thr, base, path, max_bytes)` — throttled, GET,
  never raises, `client.stream()` with a real byte cap. `lib/inventory.py`: functions +
  `MAX_CHUNKS = 100`, `MAX_CHUNK_BYTES = 2_000_000`. `[inventory].seed_paths` (both modes).
  `Endpoint.source: "browser" | "static-crawl" | "seed"` (consumers read only
  path/module — verified). `argparse --no-browser`; output via `inventory_file(scope)`;
  Makefile `inventory-static`. OpenAPI seed deferred to #17 (D2).
- Docs: README Two tiers, architecture.md, polyfetch-integration.md, scope.example.toml.

### Rows 7a/7b · #55 — `runners/r0_posture.py`
DoH (verified at vendor docs 2026-10-08): Cloudflare `https://cloudflare-dns.com/dns-query`
+ `Accept: application/dns-json`; Google `https://dns.google/resolve` (GET). Same JSON:
`Status, TC, RD, RA, AD, CD, Question, Answer[{name,type,TTL,data}]`; `AD` = DNSSEC
validated; Google rate-limits with 429 + `Retry-After`. `[posture].doh_urls` default
`[cloudflare, google]`; next resolver on transport error/5xx/429/non-JSON, not on NXDOMAIN.
Quad9 documents only RFC 8484 wire format → D5.
- `domains` default = `base_url` host minus leading `www.`; deeper subdomains need explicit
  list (no PSL dependency).
- 7a (`lib/posture.py` DNS half): normalise TXT (strip quotes, join split strings) before
  parsing; ≤1 SPF (RFC 7208), ≤1 DMARC at `_dmarc.<d>`, `p` ≥ `dmarc_min_policy`, DS + `AD`
  when `require_dnssec`, null MX + `v=spf1 -all` when `mail_profile="none"`, CAA present
  (issuers informational; flagged only if `caa_issuers` set, extended by
  `caa_extra_issuers`). One severity table. Runner writes `posture.jsonl` via
  `write_jsonl(scope, …)`: `{domain, check, severity, ok, detail}`.
- 7b: `lib/client.py` `get_headers(...)` (throttled, never raises, lower-cased dict); two
  GETs per domain: `http://<d>/` (no redirect follow, expect 301/308 → https, via `get()`)
  + `https://<d>/` headers: HSTS + `max-age ≥ hsts_min_max_age`, CSP, `nosniff`,
  `Referrer-Policy`, `Permissions-Policy`. `report.py` "Posture" section, `make posture`.
- Keys: issue's `[posture]` block + `domains`, `doh_urls`, `caa_issuers`. Passive only
  (DoH + 2 GETs); DoH provider sees target domain names — document in architecture.md.

## Source map (verified 2026-10-08, HEAD 05e5c43)

- `lib/client.py`: `ROOT` :22, `SCOPE_ENV` :23, `scope_path()` :26-29, `load_scope()`
  :32-40, `get()` (caps `body` at 400 chars) / `get_json()` / `Throttle` mid-file,
  `load_endpoints()` :165-167 (`ROOT/inventory/api_endpoints.json`), `write_jsonl()` :170-174
  (`ROOT/results/`, `mkdir` without `parents`). Accessor pattern to copy: `admin_prefixes`,
  `inventory_prefixes`.
- Callers: `r2_authmatrix.py` imports :20/:23, `load_endpoints` :33, `ep[...]` :47,
  `write_jsonl` :51 · `r2_cron_auth.py` :20, :35, :41-46 · `r3_bola.py` `write_jsonl` :70 ·
  `r3_rbac_bfla.py` :22/:24, :39, :46-57. `r2_schemathesis.sh`: no results/inventory paths.
- `runners/r1_recon.py`: `ROOT` :16, `sys.path` :17, `shots` :50-51, screenshot :85,
  `recon.jsonl` :94-96.
- `inventory/build_inventory.py`: `ROOT` :17, `sys.path` :18, module-level
  `require_render_session()` (~:25), `_harvest_js(host)` (performance-entries JS),
  `mine()` ~:50, loud-zero print :60, output :71-73.
- `lib/inventory.py`: `path_pattern`, `harvest_paths(chunks, prefixes)` (keep unchanged).
  `lib/browser.py`: `require_render_session()`. `lib/types.py`: `Scope`, `Endpoint` :88,
  `MatrixRow`, `CookieFinding`, `InventoryCfg`, …
- `report.py`: `ROOT` :11, `RESULTS` :12, `read()` :15-20, sections, `report.md` :94-97.
- `Makefile`: `ENV ?= ./.env` :4, `LOADENV` :6 (authmatrix/cron/bola/bfla only), inventory
  :17-18, recon :20-21, report :35-36, `clean` :64-65 (root `results` only).
- `.gitignore`: `scope.toml` :7, `inventory/api_endpoints.json` :8 (root-anchored),
  `results/` :11 (any depth).
- `tests/test_client.py`: RECON_SCOPE block :179-233 (`_MINIMAL_TOML` :183-194). No test
  covers `write_jsonl`/`load_endpoints`. Other tests: test_inventory, test_bola,
  test_browser, test_cookies.
- `docs/architecture.md`: Config model :41+, CLI/env table :56 (rows :60-70), safety
  invariants :72 (git-ignored bullet :78). `README.md:96`: `scope.acme.toml` example.
- `.github/workflows/browser-tier.yml`: paths filter incl. `inventory/build_inventory.py`;
  imports `polyfetch_scrape` first, then the runners.
- Ruleset: squash-only, signed commits, required check CodeFactor (strict up-to-date).

## Access checklist + pre-staged owner gate (rows 8–9)

Rows 1–7b: only the stored `gh` credential (via the env prefix); DoH resolvers are public.
Rows 8–9 (owner: authorized target, glibc host, `make setup-browser`):
```bash
mkdir -p targets/acme && cp scope.example.toml targets/acme/scope.toml   # edit it
export RECON_SCOPE=targets/acme/scope.toml
uv run python inventory/build_inventory.py --no-browser
uv run python inventory/build_inventory.py
uv run python runners/r1_recon.py
uv run python runners/r0_posture.py
uv run python report.py
git status --short   # nothing under targets/ may show
```

## Verification (arc level)

`gh pr list` empty; 0 open alerts; #41/#55/#56 closed; `git check-ignore` matrix passes;
`pytest --cov` green, `lib/` ≥ 80 % (now 97 %); dry runs per row; 0001 shows CLOSED;
this table: rows 1–7b struck with PR numbers, 8–9 owner, D1–D5 deferred.
