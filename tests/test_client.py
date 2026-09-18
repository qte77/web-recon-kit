"""Smoke tests for the assessment harness core (lib.client, runners.r2_cron_auth)."""
import time
from collections.abc import Callable
from pathlib import Path

import httpx
import pytest

from lib.client import (
    ROOT,
    Throttle,
    _headers,
    admin_prefixes,
    bola_collectors,
    cron_prefix,
    get,
    get_json,
    identities,
    load_scope,
    public_ok,
    recon_routes,
    scope_path,
)
from lib.types import Scope
from runners.r2_cron_auth import classify


def _scope() -> Scope:
    return {
        "base_url": "https://example.test",
        "identities": {
            "owner": {"env": "TEST_OWNER", "role": "owner", "workspace": "A"},
            "tenant_b": {"env": "TEST_B", "role": "owner", "workspace": "B"},
        },
        "rate": {"max_concurrency": 4, "per_host_delay_ms": 50},
        "safety": {"methods": ["GET"]},
    }


def test_headers() -> None:
    assert _headers("abc") == {"Authorization": "Bearer abc"}
    assert _headers(None) == {}
    assert _headers("") == {}


def test_identities_resolution(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TEST_OWNER", "kvn_owner")
    monkeypatch.delenv("TEST_B", raising=False)
    ids = identities(_scope())
    assert ids["owner"]["available"] is True
    assert ids["owner"]["token"] == "kvn_owner"
    assert ids["tenant_b"]["available"] is False
    assert ids["tenant_b"]["token"] == ""


@pytest.mark.parametrize(
    ("status", "expected"),
    [(401, "GATED"), (403, "GATED"), (405, "METHOD-405"), (200, "REVIEW"), (None, "REVIEW")],
)
def test_cron_classify(status: int | None, expected: str) -> None:
    assert classify(status) == expected


async def test_throttle_spaces_requests() -> None:
    thr = Throttle(concurrency=4, delay_ms=40)
    start = time.monotonic()
    for _ in range(3):
        async with thr:
            pass
    # First acquire is immediate; the next two are spaced ~40ms each → ≥ ~70ms total.
    assert time.monotonic() - start >= 0.07


# --- Scope-accessor defaulting contract ---------------------------------------
# Every accessor must fall back to a *documented* default when its section is absent.
# These defaults decide what actually gets probed, so a silent change is a scope bug.


def test_scope_accessors_fall_back_to_documented_defaults() -> None:
    scope = _scope()  # deliberately has no [recon]/[authmatrix]/[bfla]/[bola]
    assert recon_routes(scope) == ["/"]
    assert cron_prefix(scope) == "/api/cron/"
    assert public_ok(scope) == frozenset()
    assert admin_prefixes(scope) == ("/api/admin/",)
    assert bola_collectors(scope) == []


def test_scope_accessors_honour_explicit_configuration() -> None:
    scope = _scope()
    scope["recon"] = {"routes": ["/app", "/login"], "cron_prefix": "/api/jobs/"}
    scope["authmatrix"] = {"public_ok": ["/api/health", "/api/health"]}
    scope["bfla"] = {"admin_prefixes": ["/api/root/", "/api/staff/"]}
    scope["bola"] = {"collectors": [{"list": "/api/items", "by_id": "/api/items/{id}"}]}

    assert recon_routes(scope) == ["/app", "/login"]
    assert cron_prefix(scope) == "/api/jobs/"
    assert public_ok(scope) == frozenset({"/api/health"})  # de-duplicated
    assert admin_prefixes(scope) == ("/api/root/", "/api/staff/")
    assert len(bola_collectors(scope)) == 1


# --- GET invariants -----------------------------------------------------------
# `get`/`get_json` document "never raises": a dead host must not abort a bulk run.

Handler = Callable[[httpx.Request], httpx.Response]


def _client(handler: Handler) -> httpx.AsyncClient:
    """AsyncClient wired to an in-process transport — these tests never touch the network."""
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


def _boom(_request: httpx.Request) -> httpx.Response:
    raise httpx.ConnectError("connection refused")


async def test_get_maps_response_and_truncates_body() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"content-type": "application/json", "location": "/next"},
            text="x" * 1000,
        )

    async with _client(handler) as client:
        res = await get(client, Throttle(2, 0), "https://example.test", "/api/thing")

    assert res["status"] == 200
    assert res["content_type"] == "application/json"
    assert res["location"] == "/next"
    assert len(res["body"]) == 400  # bodies are capped so results/*.jsonl stays small


async def test_get_captures_transport_error_instead_of_raising() -> None:
    async with _client(_boom) as client:
        res = await get(client, Throttle(2, 0), "https://example.test", "/api/down")

    assert res["status"] is None
    assert res["body"].startswith("ERR ")


async def test_get_omits_authorization_when_token_is_empty() -> None:
    """An unauthenticated probe must be *truly* unauthenticated — no empty Bearer."""
    seen: list[httpx.Headers] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.headers)
        return httpx.Response(204)

    async with _client(handler) as client:
        await get(client, Throttle(2, 0), "https://example.test", "/api/x", token="")

    assert "authorization" not in seen[0]


async def test_get_json_returns_none_for_non_json_body() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="<html>not json</html>")

    async with _client(handler) as client:
        status, data = await get_json(client, Throttle(2, 0), "https://example.test", "/api/x")

    assert status == 200
    assert data is None


async def test_get_json_captures_transport_error_instead_of_raising() -> None:
    async with _client(_boom) as client:
        status, data = await get_json(client, Throttle(2, 0), "https://example.test", "/api/x")

    assert status is None
    assert data is None


# --- RECON_SCOPE override -------------------------------------------------------
# `scope_path()`/`load_scope()` must default to the repo's own scope.toml, but let
# RECON_SCOPE point at any other file (relative to the caller's cwd) for multi-target use.

_MINIMAL_TOML = (
    'base_url = "https://alt.example.test"\n'
    "[identities.owner]\n"
    'env = "ALT_TOKEN"\n'
    'role = "owner"\n'
    'workspace = "A"\n'
    "[rate]\n"
    "max_concurrency = 1\n"
    "per_host_delay_ms = 0\n"
    "[safety]\n"
    'methods = ["GET"]\n'
)


@pytest.mark.parametrize("value", [None, ""])
def test_scope_path_defaults_to_repo_scope_toml(
    monkeypatch: pytest.MonkeyPatch, value: str | None
) -> None:
    if value is None:
        monkeypatch.delenv("RECON_SCOPE", raising=False)
    else:
        monkeypatch.setenv("RECON_SCOPE", value)
    assert scope_path() == ROOT / "scope.toml"


def test_load_scope_honours_recon_scope_override_absolute(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    alt = tmp_path / "alt.toml"
    alt.write_text(_MINIMAL_TOML)
    monkeypatch.setenv("RECON_SCOPE", str(alt))
    assert load_scope()["base_url"] == "https://alt.example.test"


def test_load_scope_honours_recon_scope_override_relative(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    (tmp_path / "alt.toml").write_text(_MINIMAL_TOML)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("RECON_SCOPE", "alt.toml")
    assert load_scope()["base_url"] == "https://alt.example.test"


def test_load_scope_missing_file_fails_with_resolved_path(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    missing = tmp_path / "nope.toml"
    monkeypatch.setenv("RECON_SCOPE", str(missing))
    with pytest.raises(FileNotFoundError) as excinfo:
        load_scope()
    assert str(missing.resolve()) in str(excinfo.value)
