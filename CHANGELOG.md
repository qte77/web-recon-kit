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

## [0.2.0] - 2026-07-20

### Added

- Coverage gate at the estate standard (80%), enforced by `make test` / `make check`
  and CI. Scoped to `lib/` — the shared module — because `runners/`, `inventory/` and
  `report.py` are thin CLI scripts where coverage-driven tests would be box-ticking.
- `tests/test_client.py`: contract tests for previously untested `lib.client`
  behaviour — the scope-accessor defaulting rules (which decide what actually gets
  probed), the documented "never raises" invariant on `get`/`get_json`, body
  truncation, and the guarantee that an unauthenticated probe sends no `Authorization`
  header. `lib` coverage is now 94%.

- `AGENTS.md` — guardrails for AI agents (safety invariants that may not be traded away,
  evidence-over-assertion, scope discipline). `CONTRIBUTING.md` is now explicitly the
  shared contract for humans *and* agents, and owns the testing policy and code
  conventions; `AGENTS.md` points at it rather than restating it.

- CI: `zizmor` (GitHub Actions security scanner) now runs on workflow changes, pinned and
  offline, alongside `actionlint`. Catches injection, credential-persistence, over-broad
  permissions and dangerous-trigger issues in `.github/workflows/`.

- `SECURITY.md` — vulnerability-disclosure policy for the kit itself (private reporting via
  GitHub Security Advisories, scope, supported versions). Explicitly distinguishes a flaw
  in the tool from unauthorized use of it against a target. Linked from the README.

### Changed

- `pyproject.toml`: the `browser` extra now pins `polyfetch-scrape` to the `v0.7.0`
  release tag. It previously tracked polyfetch's default branch, so browser-tier
  installs drifted silently — regenerating the lock moved it from commit `ebb84fdb`
  to the tagged `e90a8e6e`. Bump the tag deliberately to adopt a new polyfetch release.

### Fixed

- `README.md`: the "Quality gates" block claimed `make check` ran "all three" — it runs
  four (`lint`, `typecheck`, `test`, `audit`) and `make test` was missing entirely. The
  stale "(wired now, for later stages)" heading is gone; the gates run in CI today.
- `docs/architecture.md`: the CLI/env reference was missing the `changelog_*` and `clean`
  targets, `VERSION=`, and the release-workflow dispatch switches.
- `docs/roadmap.md`: moved the release pipeline, reusable-workflow/actionlint adoption
  and `uv.lock` enforcement into Delivered, and linked the remaining work to its issues.

- Docs: documented the `r2_schemathesis.sh` env switches that were missing — `BASE_URL`
  and `RECON_API_KEY` are **required** (the runner reads env, not `scope.toml`) — and
  corrected the README, which showed a broken `make -f - …` invocation for a runner that
  has no `make` target. It runs via `bash runners/r2_schemathesis.sh`.

- Release automation: dev + test tooling moved from `[project.optional-dependencies]`
  extras to a PEP 735 `[dependency-groups]` group, so `uv sync` / `uv run` install it by
  default. The bump reusable runs `uv run bump-my-version` (no `--extra`), which silently
  resolved to a base-only venv and failed with `Failed to spawn: bump-my-version` — the
  automated bump path never worked until now. `make setup` is now `uv sync`; CI drops the
  `--extra dev --extra test` flags; the `browser` runtime extra is unchanged.

### Security

- CI: the `secret-scan` checkout (`fetch-depth: 0`) now sets `persist-credentials: false`,
  fixing a credential-persistence finding (zizmor `artipacked`). gitleaks reads local
  history and authenticates via the env token, so no git credential needs to persist.

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
