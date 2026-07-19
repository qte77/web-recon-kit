# Roadmap

Delivery history + direction. Open work is tracked as GitHub issues.

## Delivered

- Target-agnostic harness: recon, auth-matrix, cron-auth, BOLA, BFLA runners; inventory
  miner; report aggregator; agentic verify workflow.
- Config-driven via `scope.toml`; two-tier (API / browser) install.
- CI: ruff + mypy `--strict` + pytest, blocking pip-audit, CodeQL, gitleaks, Dependabot;
  SHA-pinned actions. Extracted from `qte77/__kavanah_analysis` (first real engagement).

## Direction

- Adopt `qte77/.github` reusable workflows (`lint-md-links`, `validate`) + an
  **actionlint** gate on `.github/workflows/**`.
- Release pipeline (bump-my-version + scriv → tag-release), matching sibling repos.
- Pin `polyfetch-scrape` as a git submodule for fully reproducible browser-tier runs.
- More BOLA collector patterns; a schemathesis wrapper that discovers the spec.
- Coverage gate on the test suite.
