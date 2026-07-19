# User stories

## Who it serves

An **authorized security assessor** (or a product's own team) validating a web app's
API attack surface — with permission, read-only, DoS-free.

## Stories

- *As an assessor*, I enumerate a SPA's full `/api/*` surface without guessing, to
  threat-model the real endpoints — **inventory miner**.
- *As an assessor*, I see which endpoints answer unauthenticated, to spot info-exposure
  — **r2_authmatrix**.
- *As an assessor*, I confirm cron jobs reject unauthenticated calls without triggering
  destructive jobs — **r2_cron_auth** (safe GET probes).
- *As an assessor with two tenants*, I prove workspace isolation holds — or find a
  cross-tenant leak — **r3_bola**.
- *As an assessor with a low-role token*, I find admin endpoints a member can reach —
  **r3_rbac_bfla**.
- *As an assessor*, I have my own findings adversarially double-checked before writeup —
  **verify workflow**.
- *As a maintainer*, the same harness works against any target by editing one config
  file — **`scope.toml`**.

## Non-goals

- Not a scanner for unauthorized targets. Not a DoS/load tool. Not a
  mutation/exploitation framework — read-only by construction.
