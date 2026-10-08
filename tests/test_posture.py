"""Tests for lib.posture — DoH client fallback + DNS posture checks on fixture answers."""
from collections.abc import Callable, Mapping

import httpx
import pytest

from lib.client import Throttle, get_headers
from lib.posture import (
    CF_DOH,
    GOOGLE_DOH,
    check_dns,
    check_headers,
    doh_query,
    parse_caa,
    settings,
    txt_strings,
)
from lib.types import DohResponse, GetResult, PostureFinding, PostureSettings, Scope

D = "example.test"


def _scope(posture: dict[str, object] | None = None) -> Scope:
    scope: Scope = {
        "base_url": "https://www.example.test:8443",
        "identities": {},
        "rate": {"max_concurrency": 1, "per_host_delay_ms": 0},
        "safety": {"methods": ["GET"]},
    }
    if posture is not None:
        scope["posture"] = posture  # type: ignore[typeddict-item]
    return scope


def _resp(rtype: int, *data: str, ad: bool = False, status: int = 0) -> DohResponse:
    return {
        "Status": status,
        "AD": ad,
        "Answer": [{"name": D, "type": rtype, "TTL": 300, "data": d} for d in data],
    }


def _healthy() -> dict[str, DohResponse | None]:
    return {
        "TXT": _resp(16, '"v=spf1 include:_spf.mail.example.test ~all"', '"site-verification=x"'),
        "DMARC": _resp(16, '"v=DMARC1; p=quarantine; rua=mailto:d@example.test"'),
        "MX": _resp(15, "10 mx.example.test."),
        "CAA": _resp(257, '0 issue "letsencrypt.org"'),
        "DS": _resp(43, "2371 13 2 abcdef", ad=True),
    }


def _by_check(findings: list[PostureFinding]) -> Mapping[str, PostureFinding]:
    return {f["check"]: f for f in findings}


def _cfg(**over: object) -> PostureSettings:
    return settings(_scope(dict(over)))


# --- config defaults ---------------------------------------------------------------


def test_settings_defaults_domain_from_base_url_minus_www_and_port() -> None:
    cfg = settings(_scope())
    assert cfg["domains"] == ["example.test"]
    assert cfg["doh_urls"] == [CF_DOH, GOOGLE_DOH]
    assert cfg["mail_profile"] == "send"
    assert cfg["dmarc_min_policy"] == "quarantine"


# --- TXT normalisation -------------------------------------------------------------


def test_txt_strings_strips_quotes_and_joins_split_strings() -> None:
    resp = _resp(16, '"v=spf1 include:a.example.test " "include:b.example.test -all"', "bare")
    assert txt_strings(resp) == [
        "v=spf1 include:a.example.test include:b.example.test -all",
        "bare",
    ]


def test_txt_strings_ignores_non_txt_answers() -> None:
    # A CNAME in the answer chain must not be read as a TXT record.
    assert txt_strings(_resp(5, "alias.example.test.")) == []


# --- CAA parsing -------------------------------------------------------------------


@pytest.mark.parametrize(
    "data",
    [
        '0 issue "letsencrypt.org"',
        # RFC 3597 generic form: flags 00, tag-len 05, "issue", "letsencrypt.org"
        "\\# 22 00 05 69 73 73 75 65 6c 65 74 73 65 6e 63 72 79 70 74 2e 6f 72 67",
    ],
)
def test_parse_caa_presentation_and_generic_forms(data: str) -> None:
    assert parse_caa(data) == ("issue", "letsencrypt.org")


# --- DNS checks --------------------------------------------------------------------


def test_healthy_send_profile_passes_all_checks() -> None:
    findings = check_dns(D, _cfg(), _healthy())
    assert {f["check"] for f in findings} == {"spf", "dmarc", "dmarc_policy", "caa"}
    assert all(f["ok"] for f in findings), findings
    assert all(f["domain"] == D for f in findings)


def test_two_spf_records_fail() -> None:
    q = _healthy()
    q["TXT"] = _resp(16, '"v=spf1 -all"', '"v=spf1 include:x.example.test ~all"')
    spf = _by_check(check_dns(D, _cfg(), q))["spf"]
    assert not spf["ok"]
    assert "2 SPF" in spf["detail"]


def test_two_dmarc_records_fail_and_skip_policy_check() -> None:
    q = _healthy()
    q["DMARC"] = _resp(16, '"v=DMARC1; p=reject"', '"v=DMARC1; p=none"')
    by = _by_check(check_dns(D, _cfg(), q))
    assert not by["dmarc"]["ok"]
    assert "dmarc_policy" not in by


@pytest.mark.parametrize(
    ("policy", "minimum", "ok"),
    [("none", "quarantine", False), ("quarantine", "quarantine", True),
     ("reject", "quarantine", True), ("quarantine", "reject", False)],
)
def test_dmarc_policy_level(policy: str, minimum: str, ok: bool) -> None:
    q = _healthy()
    q["DMARC"] = _resp(16, f'"v=DMARC1; p={policy}"')
    by = _by_check(check_dns(D, _cfg(dmarc_min_policy=minimum), q))
    assert by["dmarc_policy"]["ok"] is ok


def _no_mail() -> dict[str, DohResponse | None]:
    q = _healthy()
    q["TXT"] = _resp(16, '"v=spf1 -all"')
    q["DMARC"] = _resp(16, '"v=DMARC1; p=reject"')
    q["MX"] = _resp(15, "0 .")
    return q


def test_no_mail_profile_requires_null_mx_hard_fail_spf_and_reject() -> None:
    by = _by_check(check_dns(D, _cfg(mail_profile="none"), _no_mail()))
    assert by["null_mx"]["ok"] and by["spf"]["ok"] and by["dmarc_policy"]["ok"]

    q = _no_mail()
    q["MX"] = _resp(15)  # no MX at all: not a null MX
    q["TXT"] = _resp(16, '"v=spf1 ~all"')
    q["DMARC"] = _resp(16, '"v=DMARC1; p=quarantine"')
    by = _by_check(check_dns(D, _cfg(mail_profile="none", dmarc_min_policy="none"), q))
    assert not by["null_mx"]["ok"]
    assert not by["spf"]["ok"]
    assert not by["dmarc_policy"]["ok"]  # "none" profile forces p=reject


def test_caa_missing_fails() -> None:
    q = _healthy()
    q["CAA"] = _resp(257)
    assert not _by_check(check_dns(D, _cfg(), q))["caa"]["ok"]


def test_caa_issuers_flagged_only_when_configured_and_extras_accepted() -> None:
    q = _healthy()
    q["CAA"] = _resp(257, '0 issue "letsencrypt.org"', '0 issuewild "pki.goog"')
    assert "caa_issuers" not in _by_check(check_dns(D, _cfg(), q))

    by = _by_check(check_dns(D, _cfg(caa_issuers=["letsencrypt.org"]), q))
    assert not by["caa_issuers"]["ok"]
    assert "pki.goog" in by["caa_issuers"]["detail"]

    cfg = _cfg(caa_issuers=["letsencrypt.org"], caa_extra_issuers=["pki.goog"])
    assert _by_check(check_dns(D, cfg, q))["caa_issuers"]["ok"]


@pytest.mark.parametrize(
    ("ds", "ok"),
    [(_resp(43, "2371 13 2 abcdef", ad=True), True),
     (_resp(43, "2371 13 2 abcdef", ad=False), False),
     (_resp(43, ad=True), False)],
)
def test_dnssec_requires_ds_and_validated_answer(ds: DohResponse, ok: bool) -> None:
    q = _healthy()
    q["DS"] = ds
    assert _by_check(check_dns(D, _cfg(require_dnssec=True), q))["dnssec"]["ok"] is ok


def test_failed_lookup_reports_dns_lookup_instead_of_a_false_missing() -> None:
    q = _healthy()
    q["TXT"] = None
    by = _by_check(check_dns(D, _cfg(), q))
    assert "spf" not in by
    assert not by["dns_lookup"]["ok"]
    assert "TXT" in by["dns_lookup"]["detail"]


# --- DoH client --------------------------------------------------------------------

Handler = Callable[[httpx.Request], httpx.Response]
_OK = {"Status": 0, "AD": True, "Answer": [{"name": D, "type": 16, "TTL": 1, "data": '"x"'}]}


async def _query(handler: Handler) -> tuple[DohResponse | None, list[str]]:
    hosts: list[str] = []

    def spy(request: httpx.Request) -> httpx.Response:
        hosts.append(request.url.host)
        assert request.headers["accept"] == "application/dns-json"
        assert request.url.params["name"] == D
        assert request.url.params["type"] == "TXT"
        return handler(request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(spy)) as client:
        res = await doh_query(client, Throttle(1, 0), [CF_DOH, GOOGLE_DOH], D, "TXT")
    return res, hosts


@pytest.mark.parametrize(
    "first",
    [
        httpx.Response(503),
        httpx.Response(429, headers={"retry-after": "5"}),
        httpx.Response(200, text="<html>not json</html>"),
    ],
)
async def test_doh_falls_back_to_next_resolver(first: httpx.Response) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return first if request.url.host == "cloudflare-dns.com" else httpx.Response(200, json=_OK)

    res, hosts = await _query(handler)
    assert res == _OK
    assert hosts == ["cloudflare-dns.com", "dns.google"]


async def test_doh_falls_back_on_transport_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "cloudflare-dns.com":
            raise httpx.ConnectError("refused")
        return httpx.Response(200, json=_OK)

    res, hosts = await _query(handler)
    assert res == _OK
    assert hosts == ["cloudflare-dns.com", "dns.google"]


async def test_doh_nxdomain_is_an_answer_not_a_fallback() -> None:
    nx = {"Status": 3, "AD": False}
    res, hosts = await _query(lambda _r: httpx.Response(200, json=nx))
    assert res == nx
    assert hosts == ["cloudflare-dns.com"]


# --- HTTP header checks (7b) -------------------------------------------------------

_GOOD_HEADERS = {
    "strict-transport-security": "max-age=31536000; includeSubDomains",
    "content-security-policy": "default-src 'self'",
    "x-content-type-options": "nosniff",
    "referrer-policy": "strict-origin-when-cross-origin",
    "permissions-policy": "camera=()",
}
_REDIRECT: GetResult = {"status": 301, "content_type": "", "body": "",
                        "location": "https://example.test/"}


def test_good_headers_and_redirect_pass() -> None:
    findings = check_headers(D, _cfg(), 200, _GOOD_HEADERS, _REDIRECT)
    assert {f["check"] for f in findings} == {
        "https_redirect", "hsts", "csp", "nosniff", "referrer_policy", "permissions_policy"}
    assert all(f["ok"] for f in findings), findings


def test_missing_headers_fail() -> None:
    by = _by_check(check_headers(D, _cfg(), 200, {"x-content-type-options": "off"}, _REDIRECT))
    for check in ("hsts", "csp", "nosniff", "referrer_policy", "permissions_policy"):
        assert not by[check]["ok"], check


@pytest.mark.parametrize(
    ("hsts", "ok"),
    [("max-age=300", False), ("max-age=15552000", True), ('max-age="31536000"', True),
     ("includeSubDomains", False)],
)
def test_hsts_max_age_threshold(hsts: str, ok: bool) -> None:
    headers = {**_GOOD_HEADERS, "strict-transport-security": hsts}
    assert _by_check(check_headers(D, _cfg(), 200, headers, _REDIRECT))["hsts"]["ok"] is ok


@pytest.mark.parametrize(
    ("status", "location", "ok"),
    [(301, "https://example.test/", True), (308, "https://example.test/", True),
     (302, "https://example.test/", False), (200, "", False),
     (301, "http://example.test/x", False)],
)
def test_http_must_permanently_redirect_to_https(status: int, location: str, ok: bool) -> None:
    http: GetResult = {"status": status, "content_type": "", "body": "", "location": location}
    by = _by_check(check_headers(D, _cfg(), 200, _GOOD_HEADERS, http))
    assert by["https_redirect"]["ok"] is ok


def test_unreachable_https_reports_fetch_failure_instead_of_missing_headers() -> None:
    by = _by_check(check_headers(D, _cfg(), None, {}, _REDIRECT))
    assert not by["headers_fetch"]["ok"]
    assert "hsts" not in by


async def test_get_headers_lowercases_and_never_raises() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, headers={"Strict-Transport-Security": "max-age=1"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        status, headers = await get_headers(client, Throttle(1, 0), "https://example.test", "/")
    assert status == 200
    assert headers["strict-transport-security"] == "max-age=1"

    def boom(_request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused")

    async with httpx.AsyncClient(transport=httpx.MockTransport(boom)) as client:
        assert await get_headers(client, Throttle(1, 0), "https://example.test", "/") == (None, {})


async def test_doh_all_resolvers_failing_returns_none() -> None:
    res, hosts = await _query(lambda _r: httpx.Response(500))
    assert res is None
    assert hosts == ["cloudflare-dns.com", "dns.google"]
