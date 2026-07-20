# web-recon-kit

[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-0.1.0-blue)](CHANGELOG.md)
[![Coverage](https://img.shields.io/badge/coverage-%E2%89%A580%25-blue)](pyproject.toml)
[![Python](https://img.shields.io/badge/python-3.11+-blue)](pyproject.toml)
[![CI](https://github.com/qte77/web-recon-kit/actions/workflows/ci.yml/badge.svg)](https://github.com/qte77/web-recon-kit/actions/workflows/ci.yml)
[![CodeQL](https://github.com/qte77/web-recon-kit/actions/workflows/codeql.yml/badge.svg)](https://github.com/qte77/web-recon-kit/actions/workflows/codeql.yml)
[![CodeFactor](https://www.codefactor.io/repository/github/qte77/web-recon-kit/badge)](https://www.codefactor.io/repository/github/qte77/web-recon-kit)
[![Lint MD and Links](https://github.com/qte77/web-recon-kit/actions/workflows/lint-md-links.yml/badge.svg)](https://github.com/qte77/web-recon-kit/actions/workflows/lint-md-links.yml)

A reusable, **target-agnostic** security-assessment harness. Runs the categories
**(1) recon**, **(2) API testing**, **(3) authz/tenant isolation** in bulk, with a
deterministic script core plus an optional agentic verification Workflow. Every
detail specific to a target — base URL, routes, identities, admin prefixes, BOLA
collectors — lives in `scope.toml`, which you configure per engagement.

> **Authorization.** Only run against a target you own or are explicitly
> authorized to test. Every runner is read-only (GET/OPTIONS), throttled, and
> never triggers cron/mutation endpoints. `results/` may contain workspace data —
> it is git-ignored. So is `scope.toml` itself, since it captures your target.

## Docs

- [Architecture](docs/architecture.md) — two tiers, components, data flow, config model, CLI/env reference
- [polyfetch integration](docs/polyfetch-integration.md) — how the browser tier uses polyfetch-scrape
- [Roadmap](docs/roadmap.md) · [User stories](docs/userstory.md) · [Glossary](docs/glossary.md)
- [Changelog](CHANGELOG.md) · [Contributing](CONTRIBUTING.md) · [Agent rules](AGENTS.md) · [Security](SECURITY.md) · [License](LICENSE) (Apache-2.0)

## Why standalone (not part of polyfetch-scrape)

`polyfetch-scrape` is a **generic** scraping engine; its own docs put "domain API
wrappers" out of scope and downstream. A target-specific pentest harness is exactly
such a downstream consumer, so it lives in its own repo and **consumes** polyfetch as
an optional `browser` extra (see [polyfetch integration](docs/polyfetch-integration.md)).
This keeps polyfetch generic and this repo's intent (and legal scope) clearly separated.

## Layout

```text
scope.example.toml          # COMMITTED template — copy to scope.toml per engagement
scope.toml                  # your target's base_url, identities, rate/safety, routes,
                             #   public-ok list, admin prefixes, BOLA collectors — git-ignored
lib/                         # typed shared core: config, throttle, async client, scope accessors
inventory/
  build_inventory.py        # (re)mine /api/* surface from JS bundles  [browser tier]
  api_endpoints.json        # generated inventory — git-ignored
runners/
  r1_recon.py               # (1) render + gate classification + screenshots  [browser]
  r2_authmatrix.py          # (2) every endpoint x every identity, GET-probed
  r2_cron_auth.py           # (2) cron auth posture (safe GET probes)
  r2_schemathesis.sh        # (2) OpenAPI fuzzing (needs the spec file)
  r3_bola.py                # (3) cross-tenant IDOR (needs 2nd workspace + scope.toml [[bola.collectors]])
  r3_rbac_bfla.py           # (3) function-level authz (needs low-role member)
report.py                   # aggregate results/*.jsonl -> results/report.md
workflow/verify_findings.workflow.js  # agentic adversarial verification (optional)
```

## Two run tiers

- **API tier** (r2/r3, report) — needs only `httpx`. `make setup`, then `uv run python …`.
- **Browser tier** (inventory, recon) — needs the optional `browser` extra, which pulls
  [polyfetch-scrape][poly] (+ patchright) from GitHub. `make setup-browser` installs it and the
  Chromium binary; API-tier users can skip it.

[poly]: https://github.com/qte77/polyfetch-scrape

## Setup

```bash
cp scope.example.toml scope.toml   # then fill in base_url, identities, routes, etc.
make setup                         # API tier: ruff, mypy, pip-audit, pytest, httpx
make setup-browser                 # (optional) browser tier: polyfetch (GitHub) + chromium
# identities live in the shared .env (never in scope.toml):
#   the env var named in [identities.owner].env      (required)
#   the env var named in [identities.tenant_b].env    (for BOLA — provision a 2nd workspace)
#   the env var named in [identities.lowrole].env     (for BFLA — optional)
```

## Run

```bash
make inventory        # refresh the endpoint inventory (browser tier)
make authmatrix       # (2) auth posture over all endpoints
make cron             # (2) cron auth posture
make bola             # (3) cross-tenant — skips cleanly if the tenant_b identity is unset
make bfla             # (3) BFLA        — skips cleanly if the lowrole identity is unset
make recon            # (1) gate classification + screenshots (browser tier)
make report           # -> results/report.md
make all              # authmatrix + cron + bola + bfla + report
```

Override the env-file location: `make authmatrix ENV=/path/to/.env`.

## Fork / bulk model

- **Bulk** = one config-driven endpoint list fanned out by an `asyncio` worker pool
  (`lib.Throttle`, `max_concurrency` in `scope.toml`) with polite per-host spacing.
- **Fork** = that pool at the script level; at the agentic level,
  `workflow/verify_findings.workflow.js` fans out `parallel()` verifier panels per
  candidate finding (pass candidates via `args`; Workflow scripts can't read files).

## Quality gates

All four run in CI on every PR:

```bash
make lint         # ruff  (E,F,I,B,UP,ANN,S,RUF,PTH)
make typecheck    # mypy --strict
make test         # pytest + coverage gate (80% over lib/, see pyproject.toml)
make audit        # pip-audit (SCA)
make check        # all four
```

## Category-2/3 prerequisites

- **BOLA (r3_bola):** needs a **second workspace** (the `tenant_b` identity) and
  `[[bola.collectors]]` entries in `scope.toml`. With one identity there is no
  other tenant to prove isolation against.
- **schemathesis (r2_schemathesis):** a standalone bash runner (not a `make` target),
  driven by env vars rather than `scope.toml`. Needs the target's OpenAPI spec — usually
  repo-only, not served publicly. Obtain it, then:

  ```bash
  BASE_URL=https://target.example.com RECON_API_KEY=… SPEC=/path/openapi.yaml \
    bash runners/r2_schemathesis.sh
  ```

  `BASE_URL`, `RECON_API_KEY`, `SPEC` are required (`RECON_API_KEY` may instead be sourced
  via `ENV=/path/.env`). Mutating methods are excluded by default; see the switch table in
  [architecture](docs/architecture.md#cli--env-reference).
