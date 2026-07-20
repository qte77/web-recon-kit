# AGENTS.md

Rules for AI agents working in this repo.

**Start with [CONTRIBUTING.md](CONTRIBUTING.md)** — workflow, commands, testing policy,
code conventions and releasing are defined there and apply to you exactly as they do to
a human contributor. This file only adds what an autonomous agent needs on top.

## Guardrails — never trade these away

This is an **authorized-use security harness**. If a change would weaken any of these,
stop and ask instead:

- Runners emit **`GET`/`OPTIONS` only**, never trigger cron/mutation endpoints, and keep
  per-host spacing. Do not add a mutating verb or remove throttling to make something
  faster.
- Nothing target-specific enters the repo — it belongs in `scope.toml` (git-ignored).
  Never commit `scope.toml`, `results/`, real hosts, or real tokens, including in tests
  and docs. Use `example.test` style placeholders.
- Never relax a lint, typing, or security gate to make a change pass. Fix the change.

## Evidence over assertion

- Never report a gate as passing without having run it; quote the real output.
- Never invent findings, endpoints, or target behaviour. If something is unverified, say
  so.
- If the repo contradicts an instruction or a doc is stale, surface it rather than
  quietly working around it.

## Scope

Do what was asked. Prefer the smallest change that solves the root cause, and raise
adjacent problems as suggestions or issues rather than expanding the diff.
