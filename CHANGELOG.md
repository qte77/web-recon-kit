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

## [0.3.2] - 2026-10-08

### Fixed

- `r0_posture`: a silent `http://<d>/` no longer counts as a pass. A refused connection
  still passes the redirect check (port 80 closed); a timeout, DNS or other failure is now
  an inconclusive `http_probe` finding (`info`). `lib/client.py` `probe()` reports why a
  GET got no response.

- `make lint-md`: only existing `.md` files go to lychee. A tracked file deleted but not
  yet staged (e.g. fragments `scriv collect` just removed) was read as a URL and crashed
  the offline link check; untracked, non-ignored `.md` files are now checked too.

## [0.3.1] - 2026-10-08

### Changed

- Markdown lint uses the shared `qte77/.github` rules locally too (`make lint-md`, same
  configs CI fetches) and now covers every tracked `*.md` — CI previously linted only the
  repo root. `.markdownlint-cli2.jsonc` sets the scope; `changelog.d/` is excluded.

- Code style is now `ruff format` (as in sibling qte77 repos): one formatting-only pass
  (identical ASTs), `ruff format --check .` in CI and `make lint`, `make format` to apply.

### Fixed

- `report.py`: sections with no results no longer leave runs of blank lines in
  `results/report.md`, which now ends with a single newline (markdownlint-clean).

### Security

- `inventory/build_inventory.py` (browser mode): bundle URLs are kept only on an exact
  http(s) host match with `base_url`, like the `--no-browser` crawl — the old substring
  test also accepted look-alike hosts such as `<host>.evil.test` (#66).

## [0.3.0] - 2026-10-08

### Added

- `lib/client.py`: `RECON_SCOPE` selects the scope file (default `scope.toml`), relative to
  the shell's cwd — lets one checkout assess multiple targets without copying files. A
  missing override file aborts with the resolved path in the error message.

- `inventory/build_inventory.py`: `[inventory].path_prefixes` selects which literal path
  prefixes get mined from JS bundles (default `/api/`) — targets whose endpoints live under
  a different prefix no longer get a silently-empty inventory. An empty harvest now warns
  ("mined 0 endpoints from N JS files — check [inventory].path_prefixes") instead of
  producing a quietly-clean-looking run. Mining logic moved to the new `lib/inventory.py`.

- `runners/r3_bola.py`: `[[bola.collectors]]` entries accept a dotted `collection_key`
  (e.g. `data.result.items`) for nested response bodies, and an optional `id_field`
  (default `id`) for collections keyed on something other than `id`. Extraction logic moved
  to the new `lib/bola.py`.

- `runners/r1_recon.py`: `results/recon.jsonl` rows now carry per-route `console_errors`
  (error-level console messages + uncaught page errors, from polyfetch's session capture).
  Vantage-scoped — reflects only this runner's own headless network. `report.py`'s recon
  section now also prints the count.

- `lib/cookies.py`, `runners/r1_recon.py`: per-route `cookie_findings` in
  `results/recon.jsonl` — document-response cookies missing `HttpOnly`/`Secure` or with
  `SameSite=None`/unset (read from `Set-Cookie` headers, never `page.evaluate`;
  vantage-scoped like `console_errors`).

- `.github/workflows/browser-tier.yml`: paths-filtered + weekly import smoke of the optional
  `browser` extra, catching polyfetch API breakage without slowing normal PRs down with a
  Chromium download on every push.

- `lib/client.py`: `results/` and `inventory/` now live next to the scope file, so
  `RECON_SCOPE=targets/<name>/scope.toml` keeps each target's outputs separate (default
  `./scope.toml` → repo root, unchanged). Optional `[output].dir` overrides the location.
  `load_endpoints`/`write_jsonl` take the scope; `write_jsonl` creates nested dirs;
  `r1_recon`, `build_inventory` and `report.py` follow the same location (#41).

- `inventory/build_inventory.py --no-browser` (`make inventory-static`): builds the
  endpoint inventory without Chromium by fetching the entry HTML and following on-host
  code-split JS chunks (`<script src>`, `modulepreload`, `import("./x.js")`, `from"./y.js"`,
  `"/assets/z.js"`) with throttled GETs, capped at 100 chunks × 2 MB (`lib/inventory.py`
  `crawl`, `lib/client.py` `get_text`). `[inventory].seed_paths` appends known paths in
  both modes; each endpoint now records `source` (`browser` / `static-crawl` / `seed`).
  The browser import is now lazy, so `--no-browser` runs without the `browser` extra (#56).

- `runners/r0_posture.py` + `lib/posture.py`: passive DNS posture per domain via public
  DNS-over-HTTPS (Cloudflare, then Google; `[posture].doh_urls`) — at most one SPF and
  one DMARC record, DMARC policy level, null MX + `v=spf1 -all` for `mail_profile = "none"`,
  CAA present (issuers flagged only when `caa_issuers` is set), DS + validated (`AD`)
  answers when `require_dnssec`. Writes `results/posture.jsonl` (#55).

- `runners/r0_posture.py`: HTTP posture per domain — `http://<d>/` must 301/308 to
  https, and `https://<d>/` must send HSTS (`max-age` ≥ `[posture].hsts_min_max_age`),
  CSP, `X-Content-Type-Options: nosniff`, `Referrer-Policy` and `Permissions-Policy`
  (two GETs, redirects not followed; `lib/client.py` `get_headers`). `report.py` gains a
  "Posture" section; `make posture` runs it (#55).

### Fixed

- `report.py`: the aggregate `Auth matrix` section no longer lists paths whitelisted in
  `scope.toml`'s `[authmatrix].public_ok` as findings needing review. `r2_authmatrix.py`
  already excluded them from its own console output but never persisted that decision into
  `results/authmatrix.jsonl`, so `report.py` (which has no access to `scope.toml`) recomputed
  exposure from raw status codes alone and disagreed with the runner's own live output.

- `runners/r1_recon.py`, `inventory/build_inventory.py`: a missing `polyfetch_scrape` now
  exits 2 with the install command and the musllinux caveat (`lib/browser.py`) instead of a
  raw `ImportError`.

### Security

- `.gitignore`: ignore `scope.*.toml` (except `scope.example.toml`) and
  `inventory/api_endpoints.json` at any depth, so per-target scope files and inventories
  can no longer be committed by accident.

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
