"""Pure Set-Cookie security-flag audit for runners/r1_recon.py (mypy --strict clean)."""
from __future__ import annotations

from collections.abc import Sequence

from lib.types import CookieFinding


def parse_set_cookie(header: str) -> CookieFinding | None:
    """Parse one Set-Cookie header into its security-relevant flags, or None if malformed."""
    parts = [p.strip() for p in header.split(";")]
    if not parts or "=" not in parts[0]:
        return None
    name, _, value = parts[0].partition("=")
    name = name.strip()
    if not name or not value.strip():
        return None

    attrs: dict[str, str] = {}
    for part in parts[1:]:
        key, _, val = part.partition("=")
        attrs[key.strip().lower()] = val.strip()

    return {
        "name": name,
        "missing_httponly": "httponly" not in attrs,
        "missing_secure": "secure" not in attrs,
        "samesite": attrs.get("samesite", "").lower() or "unset",
    }


def audit_set_cookie(headers: Sequence[str]) -> list[CookieFinding]:
    """Parse every Set-Cookie header and keep only the ones with a weak flag."""
    findings: list[CookieFinding] = []
    for header in headers:
        finding = parse_set_cookie(header)
        if finding is None:
            continue
        if finding["missing_httponly"] or finding["missing_secure"] or (
            finding["samesite"] in {"none", "unset"}
        ):
            findings.append(finding)
    return findings
