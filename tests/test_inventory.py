"""Tests for lib.inventory's JS-bundle path-mining logic (pure, no network)."""
from lib.inventory import harvest_paths


def test_harvest_paths_matches_only_configured_prefixes_deduped_sorted() -> None:
    chunks = {
        "a.js": (
            'fetch("/api/users/"); x=\'/v1/items\'; y=`/internal/x`; z="/api/users"'
        ),
    }
    assert harvest_paths(chunks, ("/api/", "/v1/")) == ["/api/users", "/v1/items"]


def test_harvest_paths_escapes_prefix_metacharacters() -> None:
    chunks = {"a.js": '"/v1.0/thing" "/v1x0/other"'}
    # A literal "." in the configured prefix must not match "x" — no unintended regex.
    assert harvest_paths(chunks, ("/v1.0/",)) == ["/v1.0/thing"]


def test_harvest_paths_empty_prefixes_yield_nothing() -> None:
    chunks = {"a.js": '"/api/users"'}
    assert harvest_paths(chunks, ()) == []


def test_harvest_paths_ignores_non_string_chunk_values() -> None:
    chunks: dict[str, object] = {"a.js": None, "b.js": '"/api/x"'}
    assert harvest_paths(chunks, ("/api/",)) == ["/api/x"]
