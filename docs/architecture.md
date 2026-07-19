# Architecture

`web-recon-kit` is a **target-agnostic** security-assessment harness: a deterministic
script core plus an optional agentic verification layer. Everything target-specific
lives in `scope.toml` (copy from `scope.example.toml`); secrets live only in the
environment.

## Two tiers

| Tier | Runtime | Runners | Install |
|---|---|---|---|
| **API** | `httpx` (own venv) | r2_authmatrix, r2_cron_auth, r2_schemathesis, r3_bola, r3_rbac_bfla, report | `make setup` |
| **Browser** | patchright/Chromium via [polyfetch-scrape][poly] | inventory miner, r1_recon | `make setup-browser` |

The browser tier is an optional `browser` extra so API-tier users never install
Chromium. See [polyfetch integration](polyfetch-integration.md) for how the runners
use polyfetch (bundle mining, gate classification, screenshots).

[poly]: https://github.com/qte77/polyfetch-scrape

## Components

- `lib/` — typed core (mypy `--strict`): `client.py` (throttled async httpx, identity
  resolution, scope accessors), `types.py` (TypedDict schemas).
- `inventory/build_inventory.py` — mines `/api/*` endpoints from the target's JS
  bundles → `inventory/api_endpoints.json`.
- `runners/` — one file per check; all read-only (GET/OPTIONS), throttled, config-driven.
- `report.py` — aggregates `results/*.jsonl` → `results/report.md`.
- `workflow/verify_findings.workflow.js` — agentic adversarial verification (fan-out
  judge panels; candidates passed via `args`).

## Data flow

```
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
| `[[bola.collectors]]` | list-endpoint → by-id probe templates for r3_bola |

## CLI / env reference

| Knob | Where | Effect |
|---|---|---|
| `make <target>` | Makefile | `setup setup-browser inventory recon authmatrix cron bola bfla report all lint typecheck test audit check` |
| `ENV=/path/.env` | make var | env file sourced for tokens |
| `[rate].*` | scope.toml | concurrency / per-host spacing |
| `SPEC=/path/openapi.yaml` | `r2_schemathesis.sh` | spec to fuzz (required) |
| `MAX` / `RATE` | `r2_schemathesis.sh` | max examples / rate limit |
| `EXCLUDE_MUTATING=0` | `r2_schemathesis.sh` | allow mutating methods (default `1` = GET-only) |

## Safety invariants

- Runners only ever emit `GET`/`OPTIONS` (`[safety].methods`).
- Cron/mutation endpoints are never triggered; the cron POST-with-invalid-secret test
  is a deliberate, gated manual step.
- Per-host spacing keeps load far below any DoS threshold.
- `results/`, `scope.toml`, and `inventory/api_endpoints.json` are git-ignored.
