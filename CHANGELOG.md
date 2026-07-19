# Changelog

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Date/PR-based until a
first tagged release.

## [Unreleased]

### Added

- Docs: `docs/architecture.md` (design, config model, CLI/env reference),
  `docs/roadmap.md`, `docs/userstory.md`, `CHANGELOG.md`, Apache-2.0 `LICENSE`.

## 2026-07-18

### Added

- Initial extraction of the target-agnostic web-recon harness from
  `qte77/__kavanah_analysis`: `lib/`, `runners/` (r1_recon, r2_authmatrix, r2_cron_auth,
  r2_schemathesis, r3_bola, r3_rbac_bfla), `inventory/build_inventory.py`, `report.py`,
  `workflow/verify_findings.workflow.js`, `tests/`, `scope.example.toml`.
- CI: ruff, mypy `--strict`, pytest, pip-audit, CodeQL, gitleaks, Dependabot;
  SHA-pinned actions. Two-tier setup (`make setup` / `make setup-browser`).
