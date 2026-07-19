# Contributing

Behavioural rules for AI agents live in the workspace `.claude/rules/` (loaded via
`CLAUDE.md`). This file covers the human contributor workflow.

## Documentation hierarchy

One audience per file — reference, don't duplicate (estate contract:
[doc-structure.md](https://github.com/qte77/qte77/blob/main/docs/doc-structure.md)):

| File | Audience | Owns |
| --- | --- | --- |
| [README.md](README.md) | users / evaluators | what this is, why, how — the front door |
| CONTRIBUTING.md (this file) | contributors | workflow, commands, conventions, releasing |
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

## Conventional Commits

`feat`, `fix`, `docs`, `chore`, `refactor`. Optional scope: `feat(SCOPE): ...`. PR titles match.

## Branches

- `feat/TOPIC`, `fix/TOPIC`, `docs/TOPIC`, `chore/TOPIC`
- Squash-merge is default. Force-push only with `--force-with-lease`, never to `main`.

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
