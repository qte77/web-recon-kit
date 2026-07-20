### Fixed

- Release automation: dev + test tooling moved from `[project.optional-dependencies]`
  extras to a PEP 735 `[dependency-groups]` group, so `uv sync` / `uv run` install it by
  default. The bump reusable runs `uv run bump-my-version` (no `--extra`), which silently
  resolved to a base-only venv and failed with `Failed to spawn: bump-my-version` — the
  automated bump path never worked until now. `make setup` is now `uv sync`; CI drops the
  `--extra dev --extra test` flags; the `browser` runtime extra is unchanged.
