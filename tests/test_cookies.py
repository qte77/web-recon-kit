"""Tests for lib.cookies' Set-Cookie security-flag audit (pure, no network)."""
import pytest

from lib.cookies import audit_set_cookie, parse_set_cookie


@pytest.mark.parametrize(
    ("header", "expected"),
    [
        (
            "sid=a; Path=/; HttpOnly; Secure; SameSite=Lax",
            {"name": "sid", "missing_httponly": False, "missing_secure": False,
             "samesite": "lax"},
        ),
        (
            "sid=a; Secure; SameSite=Lax",
            {"name": "sid", "missing_httponly": True, "missing_secure": False,
             "samesite": "lax"},
        ),
        (
            "sid=a; HttpOnly; SameSite=Strict",
            {"name": "sid", "missing_httponly": False, "missing_secure": True,
             "samesite": "strict"},
        ),
        (
            "sid=a; HttpOnly; Secure; SameSite=None",
            {"name": "sid", "missing_httponly": False, "missing_secure": False,
             "samesite": "none"},
        ),
        (
            "sid=a; HttpOnly; Secure",
            {"name": "sid", "missing_httponly": False, "missing_secure": False,
             "samesite": "unset"},
        ),
        (
            "sid=a; httponly; SECURE; samesite=lax",
            {"name": "sid", "missing_httponly": False, "missing_secure": False,
             "samesite": "lax"},
        ),
    ],
)
def test_parse_set_cookie_flags(header: str, expected: dict[str, object]) -> None:
    assert parse_set_cookie(header) == expected


@pytest.mark.parametrize("header", ["", "garbage", "=v"])
def test_parse_set_cookie_returns_none_for_malformed_header(header: str) -> None:
    assert parse_set_cookie(header) is None


def test_audit_set_cookie_omits_clean_cookies_keeps_order() -> None:
    headers = [
        "a=1; HttpOnly; Secure; SameSite=Lax",  # clean -> omitted
        "b=2; Secure; SameSite=Lax",            # missing HttpOnly
        "c=3; HttpOnly; Secure",                # SameSite unset
    ]
    findings = audit_set_cookie(headers)
    assert [f["name"] for f in findings] == ["b", "c"]
    assert findings[0]["missing_httponly"] is True
    assert findings[1]["samesite"] == "unset"


def test_audit_set_cookie_skips_malformed_headers_alongside_a_clean_cookie() -> None:
    clean = "a=1; HttpOnly; Secure; SameSite=Lax"
    assert audit_set_cookie(["", "garbage", clean]) == []
