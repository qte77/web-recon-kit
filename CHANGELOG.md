# Changelog

All notable changes to this project are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Types of changes:

- `Added` for new features.
- `Changed` for changes in existing functionality.
- `Deprecated` for soon-to-be removed features.
- `Removed` for now removed features.
- `Fixed` for any bugfixes.
- `Security` in case of vulnerabilities.

<!-- scriv-insert-here -->

## [0.1.0] - 2026-07-19

### Added

- Initial extraction of the target-agnostic web-recon harness from
  `qte77/__kavanah_analysis`: `lib/`, `runners/` (r1_recon, r2_authmatrix, r2_cron_auth,
  r2_schemathesis, r3_bola, r3_rbac_bfla), `inventory/build_inventory.py`, `report.py`,
  `workflow/verify_findings.workflow.js`, `tests/`, `scope.example.toml`.
- CI: ruff, mypy `--strict`, pytest, pip-audit, CodeQL, gitleaks, Dependabot;
  SHA-pinned actions. Two-tier setup (`make setup` / `make setup-browser`).
- Docs: `docs/architecture.md` (design, config model, CLI/env reference),
  `docs/roadmap.md`, `docs/userstory.md`, `docs/glossary.md`,
  `docs/polyfetch-integration.md` (browser-tier polyfetch usage), `CHANGELOG.md`,
  Apache-2.0 `LICENSE`.
- Release automation: estate-standard `bump-my-version` / `tag-release` /
  `publish-release` workflows (thin callers into `qte77/.github` reusables),
  `[tool.bumpversion]` + `[tool.scriv]` (`changelog.d/` fragments), a README version
  badge, and `CONTRIBUTING.md`.

### Fixed

- Docs: corrected stale `env-borrow` / `POLY=/path` references left after the move to
  the optional `browser` extra (#5) — README "Why standalone", the `r1_recon` and
  `build_inventory` docstrings, the mypy-override comment, and the glossary now describe
  `uv sync --extra browser`.
