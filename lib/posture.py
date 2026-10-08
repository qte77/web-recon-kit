"""Passive host posture: DNS-over-HTTPS client, DNS checks and HTTP security-header
checks (mypy --strict clean).

DNS lookups go to public DoH resolvers (JSON API), never to the target; the target gets
only `GET http://<d>/` + `GET https://<d>/`. A failed lookup or fetch is reported as
`dns_lookup` / `headers_fetch`, never as a missing record or header.
"""
from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import cast
from urllib.parse import urlparse

import httpx

from lib.client import Throttle
from lib.types import (
    DmarcPolicy,
    DohResponse,
    GetResult,
    PostureFinding,
    PostureSettings,
    Scope,
    Severity,
)

CF_DOH = "https://cloudflare-dns.com/dns-query"
GOOGLE_DOH = "https://dns.google/resolve"

# label -> (query name template, record type). check_dns reads results by label.
QUERIES: dict[str, tuple[str, str]] = {
    "TXT": ("{d}", "TXT"),
    "DMARC": ("_dmarc.{d}", "TXT"),
    "MX": ("{d}", "MX"),
    "CAA": ("{d}", "CAA"),
    "DS": ("{d}", "DS"),
}
_RTYPE = {"TXT": 16, "MX": 15, "DS": 43, "CAA": 257}

# The one severity table: a failing check's severity.
SEVERITY: dict[str, Severity] = {
    "dns_lookup": "info",
    "spf": "medium",
    "dmarc": "medium",
    "dmarc_policy": "medium",
    "null_mx": "low",
    "caa": "low",
    "caa_issuers": "low",
    "dnssec": "low",
    "headers_fetch": "info",
    "https_redirect": "medium",
    "hsts": "medium",
    "csp": "low",
    "nosniff": "low",
    "referrer_policy": "info",
    "permissions_policy": "info",
}

_MAX_AGE = re.compile(r'max-age\s*=\s*"?(\d+)"?', re.IGNORECASE)

_DMARC_RANK: dict[str, int] = {"none": 0, "quarantine": 1, "reject": 2}
_QUOTED = re.compile(r'"((?:[^"\\]|\\.)*)"')


def settings(scope: Scope) -> PostureSettings:
    cfg = scope.get("posture") or {}
    host = urlparse(scope["base_url"]).hostname or ""
    return {
        "domains": list(cfg.get("domains") or [host.removeprefix("www.")]),
        "doh_urls": list(cfg.get("doh_urls") or [CF_DOH, GOOGLE_DOH]),
        "mail_profile": cfg.get("mail_profile", "send"),
        "dmarc_min_policy": cfg.get("dmarc_min_policy", "quarantine"),
        "require_caa": cfg.get("require_caa", True),
        "require_dnssec": cfg.get("require_dnssec", False),
        "hsts_min_max_age": cfg.get("hsts_min_max_age", 15_552_000),
        "caa_issuers": list(cfg.get("caa_issuers", [])),
        "caa_extra_issuers": list(cfg.get("caa_extra_issuers", [])),
    }


async def doh_query(
    client: httpx.AsyncClient,
    throttle: Throttle,
    doh_urls: Sequence[str],
    name: str,
    rtype: str,
    timeout: int = 10,
) -> DohResponse | None:
    """First usable DoH JSON answer, trying resolvers in order. Falls through on
    transport error / non-200 (5xx, 429) / non-JSON; an NXDOMAIN is an answer."""
    for url in doh_urls:
        async with throttle:
            try:
                r = await client.get(
                    url, params={"name": name, "type": rtype},
                    headers={"Accept": "application/dns-json"}, timeout=timeout,
                )
            except (httpx.HTTPError, OSError):
                continue
        if r.status_code != 200:
            continue
        try:
            data: object = r.json()
        except ValueError:
            continue
        if isinstance(data, dict) and isinstance(data.get("Status"), int):
            return cast(DohResponse, data)
    return None


def _data(resp: DohResponse, rtype: int) -> list[str]:
    return [a["data"] for a in resp.get("Answer", []) if a.get("type") == rtype]


def txt_strings(resp: DohResponse) -> list[str]:
    """TXT records with quotes stripped and split character-strings joined."""
    out = []
    for raw in _data(resp, _RTYPE["TXT"]):
        parts = _QUOTED.findall(raw)
        out.append("".join(parts) if parts else raw)
    return out


def parse_caa(data: str) -> tuple[str, str] | None:
    """(tag, value) from presentation form (`0 issue "ca.test"`) or the RFC 3597
    generic form (`\\# <len> <hex>`) some resolvers return."""
    if data.startswith("\\#"):
        try:
            raw = bytes.fromhex("".join(data.split()[2:]))
        except ValueError:
            return None
        if len(raw) < 2:
            return None
        tag_len = raw[1]
        tag = raw[2:2 + tag_len].decode(errors="replace")
        return tag.lower(), raw[2 + tag_len:].decode(errors="replace")
    parts = data.split(None, 2)
    if len(parts) != 3:
        return None
    return parts[1].lower(), parts[2].strip('"')


def _is_spf(txt: str) -> bool:
    return txt.lower() == "v=spf1" or txt.lower().startswith("v=spf1 ")


def _dmarc_tags(record: str) -> dict[str, str]:
    tags = {}
    for part in record.split(";"):
        key, sep, value = part.partition("=")
        if sep:
            tags[key.strip().lower()] = value.strip()
    return tags


def _finding(domain: str, check: str, ok: bool, detail: str) -> PostureFinding:
    return {"domain": domain, "check": check, "severity": SEVERITY[check], "ok": ok,
            "detail": detail}


def check_dns(
    domain: str, cfg: PostureSettings, q: Mapping[str, DohResponse | None]
) -> list[PostureFinding]:
    """Posture findings for one domain from DoH results keyed by QUERIES label."""
    out: list[PostureFinding] = []
    no_mail = cfg["mail_profile"] == "none"
    failed = [label for label in QUERIES if q.get(label) is None]
    if failed:
        out.append(_finding(domain, "dns_lookup", False,
                            f"DoH lookup failed on every resolver: {', '.join(failed)}"))

    if (txt := q.get("TXT")) is not None:
        spf = [t for t in txt_strings(txt) if _is_spf(t)]
        ok = len(spf) == 1 and (not no_mail or spf[0].split() == ["v=spf1", "-all"])
        want = '"v=spf1 -all"' if no_mail else "exactly 1"
        out.append(_finding(domain, "spf", ok, f"{len(spf)} SPF record(s), want {want}: {spf}"))

    if (dm := q.get("DMARC")) is not None:
        records = [t for t in txt_strings(dm) if t.lower().startswith("v=dmarc1")]
        out.append(_finding(domain, "dmarc", len(records) == 1,
                            f"{len(records)} DMARC record(s) at _dmarc.{domain}, want exactly 1"))
        if len(records) == 1:
            policy = _dmarc_tags(records[0]).get("p", "").lower()
            minimum: DmarcPolicy = "reject" if no_mail else cfg["dmarc_min_policy"]
            ok = _DMARC_RANK.get(policy, -1) >= _DMARC_RANK[minimum]
            detail = f"p={policy or '?'}, want >= {minimum}"
            out.append(_finding(domain, "dmarc_policy", ok, detail))

    if no_mail and (mx := q.get("MX")) is not None:
        records = [" ".join(r.split()) for r in _data(mx, _RTYPE["MX"])]
        out.append(_finding(domain, "null_mx", records == ["0 ."],
                            f"MX {records}, want a null MX (RFC 7505: 0 .)"))

    if (caa := q.get("CAA")) is not None:
        parsed = [p for p in map(parse_caa, _data(caa, _RTYPE["CAA"])) if p]
        issuers = sorted({v.split(";")[0].strip() for t, v in parsed
                          if t in ("issue", "issuewild")})
        if cfg["require_caa"]:
            out.append(_finding(domain, "caa", bool(parsed), f"CAA issuers: {issuers or 'none'}"))
        if cfg["caa_issuers"]:
            allowed = set(cfg["caa_issuers"]) | set(cfg["caa_extra_issuers"])
            unexpected = [i for i in issuers if i and i not in allowed]
            out.append(_finding(domain, "caa_issuers", not unexpected,
                                f"unexpected CAA issuers: {unexpected or 'none'}"))

    if cfg["require_dnssec"] and (ds := q.get("DS")) is not None:
        has_ds = bool(_data(ds, _RTYPE["DS"]))
        validated = bool(ds.get("AD"))
        out.append(_finding(domain, "dnssec", has_ds and validated,
                            f"DS {'present' if has_ds else 'missing'}, "
                            f"AD {'set' if validated else 'unset'}"))
    return out


def check_headers(
    domain: str,
    cfg: PostureSettings,
    https_status: int | None,
    headers: Mapping[str, str],
    http: GetResult,
) -> list[PostureFinding]:
    """Findings from `GET https://<d>/` (status + lower-cased headers, no redirect
    follow) and `GET http://<d>/` (expected: a 301/308 to https)."""
    out: list[PostureFinding] = []
    if http["status"] is None:
        out.append(_finding(domain, "https_redirect", True,
                            "no plain-HTTP response (port 80 unreachable)"))
    else:
        ok = http["status"] in (301, 308) and http["location"].startswith("https://")
        out.append(_finding(domain, "https_redirect", ok,
                            f"http:// -> {http['status']} {http['location'] or '(no Location)'}"
                            ", want 301/308 to https://"))

    if https_status is None:
        out.append(_finding(domain, "headers_fetch", False, f"GET https://{domain}/ failed"))
        return out

    hsts = headers.get("strict-transport-security", "")
    m = _MAX_AGE.search(hsts)
    age = int(m.group(1)) if m else None
    sub = "includeSubDomains" if "includesubdomains" in hsts.lower() else "no includeSubDomains"
    out.append(_finding(domain, "hsts", age is not None and age >= cfg["hsts_min_max_age"],
                        f"max-age={age}, {sub}, want max-age >= {cfg['hsts_min_max_age']}"
                        if hsts else "Strict-Transport-Security missing"))
    nosniff = headers.get("x-content-type-options", "")
    out.append(_finding(domain, "nosniff", nosniff.strip().lower() == "nosniff",
                        f"X-Content-Type-Options: {nosniff or 'missing'}"))
    for check, name in (("csp", "content-security-policy"),
                        ("referrer_policy", "referrer-policy"),
                        ("permissions_policy", "permissions-policy")):
        out.append(_finding(domain, check, name in headers,
                            f"{name}: {'present' if name in headers else 'missing'}"))
    return out
