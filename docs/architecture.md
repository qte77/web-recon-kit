# Architecture

`web-recon-kit` is a **target-agnostic** security-assessment harness: a deterministic
script core plus an optional agentic verification layer. Everything target-specific
lives in `scope.toml` (copy from `scope.example.toml`); secrets live only in the
environment.

## Two tiers

| Tier | Runtime | Runners | Install |
|---|---|---|---|
| **API** | `httpx` (own venv) | r0_posture, r2_authmatrix, r2_cron_auth, r2_schemathesis, r3_bola, r3_rbac_bfla, report | `make setup` |
| **Browser** | patchright/Chromium via [polyfetch-scrape][poly] | inventory miner, r1_recon | `make setup-browser` |

The inventory miner also runs on the API tier with `--no-browser` (`make inventory-static`):
a static crawl of the entry HTML's on-host code-split JS chunks (≤ 100 chunks × 2 MB).
Each endpoint records its `source`: `browser`, `static-crawl`, or `seed`.

The browser tier is an optional `browser` extra so API-tier users never install
Chromium. See [polyfetch integration](polyfetch-integration.md) for how the runners
use polyfetch (bundle mining, gate classification, screenshots).

[poly]: https://github.com/qte77/polyfetch-scrape

## Components

- `lib/` — typed core (mypy `--strict`): `client.py` (throttled async httpx, identity
  resolution, scope accessors), `types.py` (TypedDict schemas), `inventory.py`
  (JS-bundle path-mining, pure).
- `inventory/build_inventory.py` — mines endpoints under `[inventory].path_prefixes`
  (default `/api/`) from the target's JS bundles → `inventory/api_endpoints.json`
  (all outputs are relative to the scope's output dir, see `[output]`).
- `runners/` — one file per check; all read-only (GET/OPTIONS), throttled, config-driven.
- `report.py` — aggregates `results/*.jsonl` → `results/report.md`.
- `workflow/verify_findings.workflow.js` — agentic adversarial verification (fan-out
  judge panels; candidates passed via `args`).

## Data flow

```text
scope.toml ──┐
.env (tokens)─┤─> lib.load_scope ─> runners ─(read-only GETs, throttled)─> results/*.jsonl
              │                                                             ├─> report.py ─> results/report.md
              └───────────────────────────────────────────────────────────┴─> verify workflow (optional)
```

## Config model (`scope.toml`)

| Key | Purpose |
|---|---|
| `base_url` | target origin |
| `[identities.<name>]` `env` / `role` / `workspace` | token env-var name + metadata; an unset env var skips the identity |
| `[rate]` `max_concurrency` / `per_host_delay_ms` | worker-pool size / per-host spacing |
| `[safety]` `methods` | verbs runners may emit (GET/OPTIONS only) |
| `[recon]` `routes` / `cron_prefix` | routes r1_recon classifies / cron path prefix |
| `[authmatrix]` `public_ok` | endpoints where an unauthenticated 200 is expected, not a finding |
| `[bfla]` `admin_prefixes` | admin/RBAC path prefixes for r3_rbac_bfla |
| `[[bola.collectors]]` | list-endpoint → by-id probe templates for r3_bola (`collection_key` may be dotted; optional `id_field`, default `id`) |
| `[inventory]` `path_prefixes` | literal path prefixes mined from JS bundles (default `["/api/"]`) |
| `[inventory]` `seed_paths` | known paths appended to the inventory (`source: "seed"`) in both modes |
| `[posture]` `domains` / `doh_urls` / `mail_profile` / `dmarc_min_policy` / `require_caa` / `require_dnssec` / `hsts_min_max_age` / `caa_issuers` / `caa_extra_issuers` | r0_posture expectations (defaults in `scope.example.toml`) |
| `[output]` `dir` | where `results/` + `inventory/` are written (default: the scope file's directory; relative values resolve against it) |

## CLI / env reference

| Knob | Where | Effect |
|---|---|---|
| `make <target>` | Makefile | `setup setup-browser inventory inventory-static posture recon authmatrix cron bola bfla report all lint lint-md typecheck test audit check changelog_new changelog_preview changelog_release clean` |
| `ENV=/path/.env` | make var | env file sourced for tokens |
| `RECON_SCOPE=/path/scope.toml` | env (any runner) | scope file instead of `./scope.toml`; relative to the shell cwd; a missing file aborts naming the resolved path; also selects the output location (see `[output]`) |
| `--no-browser` | `build_inventory.py` (= `make inventory-static`) | static crawl of code-split JS chunks over plain GETs instead of Chromium; no `browser` extra needed |
| `VERSION=X.Y.Z` | `make changelog_release` | version the scriv fragments are collected under |
| `gh workflow run …` | GitHub Actions | release flow: `bump-my-version.yaml -f bump_type=major\|minor\|patch`, `publish-release.yaml -f tag=vX.Y.Z` — see [CONTRIBUTING](../CONTRIBUTING.md#releasing) |
| `[rate].*` | scope.toml | concurrency / per-host spacing |
| `SPEC=/path/openapi.yaml` | `r2_schemathesis.sh` | spec to fuzz (**required**) |
| `BASE_URL=https://target` | `r2_schemathesis.sh` | target origin (**required**; this runner reads env, not `scope.toml`) |
| `RECON_API_KEY=…` | `r2_schemathesis.sh` | bearer token (**required**; or source it via `ENV=/path/.env`) |
| `MAX` / `RATE` | `r2_schemathesis.sh` | max examples / rate limit (default `30` / `5/s`) |
| `EXCLUDE_MUTATING=0` | `r2_schemathesis.sh` | allow mutating methods (default `1` = GET-only) |

## Safety invariants

- Runners only ever emit `GET`/`OPTIONS` (`[safety].methods`).
- Cron/mutation endpoints are never triggered; the cron POST-with-invalid-secret test
  is a deliberate, gated manual step.
- Per-host spacing keeps load far below any DoS threshold.
- `r0_posture` is passive: DNS answers come from public DoH resolvers (`[posture].doh_urls`),
  never the target — but those resolver operators see every domain name queried. The
  target gets two GETs per domain (`http://<d>/`, `https://<d>/`, no redirect follow). A failed
  lookup is reported as `dns_lookup`, never as a missing record.
- `results/`, `scope.toml`, `scope.*.toml` (except `scope.example.toml`), and
  `inventory/api_endpoints.json` are git-ignored at any depth.
