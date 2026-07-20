# Contributing

This file is the contributor contract for **humans and AI agents alike**. Agents should
read it first, then [AGENTS.md](AGENTS.md) for the extra guardrails that apply to them.

## Documentation hierarchy

One audience per file — reference, don't duplicate (estate contract:
[doc-structure.md](https://github.com/qte77/qte77/blob/main/docs/doc-structure.md)):

| File | Audience | Owns |
| --- | --- | --- |
| [README.md](README.md) | users / evaluators | what this is, why, how — the front door |
| CONTRIBUTING.md (this file) | contributors + agents | workflow, commands, conventions, releasing |
| [AGENTS.md](AGENTS.md) | AI agents | guardrails and evidence rules on top of this file |
| [docs/](docs/) | users / operators | architecture, roadmap, glossary, polyfetch integration |
| [CHANGELOG.md](CHANGELOG.md) | everyone | notable changes by version |

## Commands

```bash
make setup          # install dev + test deps (ruff, mypy, pip-audit, pytest)
make check          # lint + typecheck + test + audit
make setup-browser  # optional browser tier (polyfetch + chromium)
markdownlint $(git ls-files '*.md')
lychee --offline $(git ls-files '*.md')
```

## Testing

- **TDD** — model the expected and desired behaviour first, then implement.
- **Only non-trivial tests.** Test behavioural contracts: defaults that decide what gets
  probed, documented invariants (`get()` "never raises"), auth guarantees. Never write a
  test to move a coverage number.
- **Test modules, not scripts.** `lib/` is the shared module and carries the 80% coverage
  gate. `runners/`, `inventory/` and `report.py` are thin CLI scripts and sit outside the
  coverage scope on purpose.
- Tests must not touch the network — use `httpx.MockTransport`.

## Code conventions

- **No `make` targets in source.** Module docstrings and comments show the direct command
  (`uv run python runners/r1_recon.py`, `uv sync --extra browser`); the Makefile is a
  convenience layer, so source must stand on its own.
- Strict lint, strict typing and dependency auditing are always-on — `make check` must be
  clean before pushing. Fix the change rather than relaxing a gate.

## Conventional Commits

`feat`, `fix`, `docs`, `chore`, `refactor`, `test`. Optional scope: `feat(SCOPE): ...`.
PR titles match.

## Branches

- `feat/TOPIC`, `fix/TOPIC`, `docs/TOPIC`, `chore/TOPIC`, `test/TOPIC`
- **One topic per branch and per commit.**
- Squash-merge only once **every** CI check passes; then delete the branch, local and
  remote. Force-push only with `--force-with-lease`, never to `main`.

## CHANGELOG

Add a `changelog.d/` fragment via `make changelog_new` for any consumer-visible change
(scriv collects them into `CHANGELOG.md` at release). Lead with the file path.

## Releasing

Semi-automatic: a **human-authored** bump PR (so the merge is a real-user event — a
`GITHUB_TOKEN` push can't retrigger the tag workflow), automatic tag, one-command publish.
SemVer; the version source of truth is `pyproject.toml [project].version`, mirrored in the
README version badge (`version-…-blue`).

1. `gh workflow run bump-my-version.yaml -f bump_type=patch|minor|major` — rewrites the
   version files, syncs `uv.lock`, collects `changelog.d/` into `CHANGELOG.md`, and opens a
   `chore(release)` PR.
2. Merge that PR → `tag-release` tags `vX.Y.Z` on the version change.
3. Optionally `gh workflow run publish-release.yaml` for a GitHub Release from the matching
   `CHANGELOG.md` block. Tag-only is fine.

The **first** release (`v0.1.0`) was tagged manually — `bump-my-version` drives every one after.

## Pre-merge

1. `make check` clean
2. `markdownlint` + `lychee --offline` clean
3. `changelog.d/` fragment added
4. Conventional Commits title
