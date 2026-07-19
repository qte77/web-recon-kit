# web-recon-kit — reusable, target-agnostic web/API assessment harness.
# API tier (auth-matrix, cron, BOLA, BFLA, report) needs only httpx.
# Browser tier (inventory, recon) needs the optional `browser` extra (polyfetch + chromium).
ENV ?= .env
PY  := uv run python
LOADENV := set -a; . $(ENV); set +a

.PHONY: setup setup-browser inventory recon authmatrix cron bola bfla report all lint typecheck test audit check changelog_new changelog_preview changelog_release clean

setup:               ## install dev + test deps (ruff, mypy, pip-audit, pytest)
	uv sync --extra dev --extra test

setup-browser:       ## install the browser tier: polyfetch (from GitHub) + chromium
	uv sync --extra dev --extra test --extra browser
	uv run patchright install chromium

inventory:           ## (re)mine the API surface from JS bundles  [needs: make setup-browser]
	$(PY) inventory/build_inventory.py

recon:               ## render routes, classify gates, screenshot  [needs: make setup-browser]
	$(PY) runners/r1_recon.py

authmatrix:          ## (2) auth-posture matrix over all endpoints
	$(LOADENV); $(PY) runners/r2_authmatrix.py

cron:                ## (2) cron-endpoint auth posture (GET, no side effects)
	$(LOADENV); $(PY) runners/r2_cron_auth.py

bola:                ## (3) cross-tenant BOLA (needs the tenant_b identity key)
	$(LOADENV); $(PY) runners/r3_bola.py

bfla:                ## (3) function-level authz on admin/RBAC (needs the lowrole identity key)
	$(LOADENV); $(PY) runners/r3_rbac_bfla.py

report:              ## aggregate results/*.jsonl -> results/report.md
	$(PY) report.py

all: authmatrix cron bola bfla report

lint:                ## ruff
	uv run ruff check .

typecheck:           ## mypy --strict
	uv run mypy

audit:               ## SCA: dependency vulnerability scan
	uv run pip-audit

test:                ## pytest smoke tests
	uv run pytest

check: lint typecheck test audit

changelog_new:       ## create + stage a new changelog fragment (scriv)
	uv run scriv create --add

changelog_preview:   ## preview the assembled release entry (scriv)
	uv run scriv print

changelog_release:   ## collect fragments into CHANGELOG.md: make changelog_release VERSION=X.Y.Z
	test -n "$(VERSION)" || { echo "usage: make changelog_release VERSION=X.Y.Z"; exit 2; }
	uv run scriv collect --version "$(VERSION)"

clean:
	rm -rf results __pycache__ */__pycache__ .mypy_cache .ruff_cache
