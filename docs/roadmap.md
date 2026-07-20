# Roadmap

Delivery history + direction. Open work is tracked as GitHub issues.

## Delivered

- Target-agnostic harness: recon, auth-matrix, cron-auth, BOLA, BFLA runners; inventory
  miner; report aggregator; agentic verify workflow.
- Config-driven via `scope.toml`; two-tier (API / browser) install.
- CI: ruff + mypy `--strict` + pytest, blocking pip-audit, CodeQL, gitleaks, Dependabot;
  SHA-pinned actions. Extracted from `qte77/__kavanah_analysis` (first real engagement).
- `polyfetch-scrape` pinned to a release tag (`@v0.7.0`) for reproducible browser-tier
  installs — a tag plus the `uv.lock`-recorded commit, rather than a git submodule.
- Coverage gate (80%) over `lib/`, the shared module. The runners and `report.py` are
  thin CLI scripts and stay out of scope rather than inviting box-ticking tests.

- `qte77/.github` reusable `lint-md-links` + an **actionlint** gate on
  `.github/workflows/**`.
- Release pipeline matching sibling repos: `bump-my-version` + scriv fragments →
  `tag-release` → `publish-release`, as thin callers into the `qte77/.github` reusables.
  First release: `v0.1.0`.
- `uv.lock` enforced in CI via `uv sync --frozen`, so the lockfile cannot drift from
  `pyproject.toml` unnoticed.

## Direction

- More BOLA collector patterns; a schemathesis wrapper that discovers the spec.
- Exercise the browser tier in CI so polyfetch API breakage is caught early ([#13](https://github.com/qte77/web-recon-kit/issues/13)).
- Standardize `uv.lock` enforcement across the estate ([qte77/.github#37](https://github.com/qte77/.github/issues/37)).
