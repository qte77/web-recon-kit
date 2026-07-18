# web-recon-kit — reusable, target-agnostic web/API assessment harness.
# API-tier runners use our own venv (httpx);
# browser-tier steps env-borrow the polyfetch clone (no venv poison).
POLY ?= /workspaces/qte77/polyfetch-scrape
ENV  ?= .env
PY_API     := uv run python
PY_BROWSER := uv run --directory $(POLY) python
LOADENV    := set -a; . $(ENV); set +a

.PHONY: setup inventory recon authmatrix cron bola bfla report all lint typecheck test audit check clean

setup:               ## install dev + test deps (ruff, mypy, pip-audit, pytest)
	uv sync --extra dev --extra test

inventory:           ## (re)mine the API surface from JS bundles  [browser tier]
	$(PY_BROWSER) $(CURDIR)/inventory/build_inventory.py

recon:               ## render routes, classify gates, screenshot  [browser tier]
	$(PY_BROWSER) $(CURDIR)/runners/r1_recon.py

authmatrix:          ## (2) auth-posture matrix over all endpoints
	$(LOADENV); $(PY_API) runners/r2_authmatrix.py

cron:                ## (2) cron-endpoint auth posture (GET, no side effects)
	$(LOADENV); $(PY_API) runners/r2_cron_auth.py

bola:                ## (3) cross-tenant BOLA (needs the tenant_b identity key)
	$(LOADENV); $(PY_API) runners/r3_bola.py

bfla:                ## (3) function-level authz on admin/RBAC (needs the lowrole identity key)
	$(LOADENV); $(PY_API) runners/r3_rbac_bfla.py

report:              ## aggregate results/*.jsonl -> results/report.md
	$(PY_API) report.py

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

clean:
	rm -rf results __pycache__ */__pycache__ .mypy_cache .ruff_cache
