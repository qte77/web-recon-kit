# Security Policy

This policy covers vulnerabilities **in web-recon-kit itself** — the harness code, its
dependencies, and its CI/release tooling. It does **not** cover findings you produce by
running the kit against a target; those belong to that target's own disclosure process.

## Reporting a vulnerability

Please report privately — **do not open a public issue** for a suspected vulnerability.

- Use GitHub's private reporting: the repository's **Security** tab → **Report a
  vulnerability** (GitHub Security Advisories).

Please include: affected version or commit, a description, reproduction steps or a proof
of concept, and the impact you see. If you have a fix in mind, say so.

This is a small project maintained on a best-effort basis — expect an initial
acknowledgement within a few days rather than on a fixed SLA. Coordinated disclosure is
appreciated: give a reasonable window for a fix before publishing.

## Supported versions

Fixes land on `main` and in the latest release. Older tags are not back-patched — pin a
release and upgrade to pick up fixes.

## Scope

In scope — the kit as shipped:

- Code in `lib/`, `runners/`, `inventory/`, `report.py`, and the `workflow/` verifier.
- A break in a **safety invariant**: e.g. a runner emitting a non-`GET`/`OPTIONS` method,
  triggering a mutation/cron endpoint, or bypassing throttling (see [README](README.md)).
- Leakage of secrets or target data by the tooling itself (tokens, `scope.toml`,
  `results/`).
- Supply-chain / CI issues (dependency confusion, workflow injection, unpinned actions).

Out of scope:

- **Using the tool against a target you are not authorized to test.** That is a misuse of
  the tool, not a vulnerability in it — the kit is read-only by construction and assumes
  an authorized engagement.
- Vulnerabilities you *discover in a target* while using the kit.
- Findings that require an already-compromised host or a modified `scope.toml` supplying
  hostile input to yourself.

Good-faith security research on the kit is welcome. Thank you for helping keep it safe.
