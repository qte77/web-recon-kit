"""Smoke tests for the assessment harness core (lib.client, runners.r2_cron_auth)."""
import time

import pytest

from lib.client import Throttle, _headers, identities
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
