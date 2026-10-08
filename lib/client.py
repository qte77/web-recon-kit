"""Shared config + throttled async HTTP client (mypy --strict clean).

Only httpx (PEP 561-typed) + stdlib. Read-only GET/OPTIONS by design.
Scope file: scope.toml at the repo root, or $RECON_SCOPE (relative to cwd).
Outputs (results/, inventory/) go next to the scope file unless `[output].dir` is set.
"""

from __future__ import annotations

import asyncio
import json
import os
import socket
import time
import tomllib
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import cast
from urllib.parse import urlparse

import httpx

from lib.types import (
    BolaCollector,
    GetResult,
    ProbeFailure,
    ProbeResult,
    ResolvedIdentity,
    Scope,
)

ROOT: Path = Path(__file__).resolve().parent.parent
SCOPE_ENV = "RECON_SCOPE"


def scope_path() -> Path:
    """$RECON_SCOPE (relative to the caller's cwd) or <repo>/scope.toml."""
    override = os.environ.get(SCOPE_ENV)
    return Path(override) if override else ROOT / "scope.toml"


def load_scope() -> Scope:
    path = scope_path()
    if not path.is_file():
        raise FileNotFoundError(
            f"scope file not found: {path.resolve()} — set {SCOPE_ENV} to a scope TOML "
            "or copy scope.example.toml to scope.toml"
        )
    with path.open("rb") as f:
        return cast(Scope, tomllib.load(f))


def target_host(scope: Scope) -> str:
    return urlparse(scope["base_url"]).netloc


def recon_routes(scope: Scope) -> list[str]:
    cfg = scope.get("recon")
    routes = cfg.get("routes") if cfg is not None else None
    return list(routes) if routes is not None else ["/"]


def cron_prefix(scope: Scope) -> str:
    cfg = scope.get("recon")
    prefix = cfg.get("cron_prefix") if cfg is not None else None
    return prefix if prefix is not None else "/api/cron/"


def public_ok(scope: Scope) -> frozenset[str]:
    cfg = scope.get("authmatrix")
    ok = cfg.get("public_ok") if cfg is not None else None
    return frozenset(ok) if ok is not None else frozenset()


def admin_prefixes(scope: Scope) -> tuple[str, ...]:
    cfg = scope.get("bfla")
    prefixes = cfg.get("admin_prefixes") if cfg is not None else None
    return tuple(prefixes) if prefixes is not None else ("/api/admin/",)


def bola_collectors(scope: Scope) -> list[BolaCollector]:
    cfg = scope.get("bola")
    collectors = cfg.get("collectors") if cfg is not None else None
    return list(collectors) if collectors is not None else []


def inventory_prefixes(scope: Scope) -> tuple[str, ...]:
    cfg = scope.get("inventory")
    prefixes = cfg.get("path_prefixes") if cfg is not None else None
    return tuple(prefixes) if prefixes is not None else ("/api/",)


def seed_paths(scope: Scope) -> list[str]:
    cfg = scope.get("inventory")
    seeds = cfg.get("seed_paths") if cfg is not None else None
    return list(seeds) if seeds is not None else []


def identities(scope: Scope) -> dict[str, ResolvedIdentity]:
    """Resolve each identity's bearer token from the environment."""
    out: dict[str, ResolvedIdentity] = {}
    for name, spec in scope["identities"].items():
        tok = os.environ.get(spec["env"], "")
        out[name] = {
            "env": spec["env"],
            "role": spec["role"],
            "workspace": spec["workspace"],
            "token": tok,
            "available": bool(tok),
        }
    return out


class Throttle:
    """Bounded concurrency + global per-host spacing (politeness / anti-DoS)."""

    def __init__(self, concurrency: int, delay_ms: int) -> None:
        self.sem: asyncio.Semaphore = asyncio.Semaphore(concurrency)
        self.delay: float = delay_ms / 1000.0
        self._last: float = 0.0
        self._lock: asyncio.Lock = asyncio.Lock()

    async def __aenter__(self) -> Throttle:
        await self.sem.acquire()
        async with self._lock:
            wait = self.delay - (time.monotonic() - self._last)
            if wait > 0:
                await asyncio.sleep(wait)
            self._last = time.monotonic()
        return self

    async def __aexit__(self, *_exc: object) -> None:
        self.sem.release()


def _headers(token: str | None) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"} if token else {}


async def get(
    client: httpx.AsyncClient,
    throttle: Throttle,
    base: str,
    path: str,
    token: str | None = None,
    timeout: int = 20,
) -> GetResult:
    """Single throttled GET. Never raises — errors are captured in the result."""
    async with throttle:
        try:
            r = await client.get(base + path, headers=_headers(token), timeout=timeout)
            return {
                "status": r.status_code,
                "content_type": r.headers.get("content-type", ""),
                "body": r.text[:400],
                "location": r.headers.get("location", ""),
            }
        except (httpx.HTTPError, OSError) as e:
            return {"status": None, "content_type": "", "body": f"ERR {e}"[:200], "location": ""}


async def get_json(
    client: httpx.AsyncClient,
    throttle: Throttle,
    base: str,
    path: str,
    token: str | None = None,
    timeout: int = 20,
) -> tuple[int | None, object]:
    """Throttled GET returning (status, parsed-json-or-None). For collectors that
    need the full body. Never raises."""
    async with throttle:
        try:
            r = await client.get(base + path, headers=_headers(token), timeout=timeout)
            try:
                data: object = r.json()
            except ValueError:
                data = None
            return r.status_code, data
        except (httpx.HTTPError, OSError):
            return None, None


async def get_headers(
    client: httpx.AsyncClient,
    throttle: Throttle,
    base: str,
    path: str,
    timeout: int = 20,
) -> tuple[int | None, dict[str, str]]:
    """Throttled GET returning (status, lower-cased response headers). The body is not
    read. (None, {}) on error. Never raises."""
    async with throttle:
        try:
            async with client.stream("GET", base + path, timeout=timeout) as r:
                return r.status_code, {k.lower(): v for k, v in r.headers.items()}
        except (httpx.HTTPError, OSError):
            return None, {}


def _failure_kind(exc: BaseException) -> ProbeFailure:
    # Reason: httpx raises ConnectError for both a refused port and a DNS failure; only
    # the underlying cause (ConnectionRefusedError vs socket.gaierror) tells them apart.
    if isinstance(exc, httpx.TimeoutException):
        return "timeout"
    seen: set[int] = set()
    cur: BaseException | None = exc
    while cur is not None and id(cur) not in seen:
        seen.add(id(cur))
        if isinstance(cur, ConnectionRefusedError):
            return "refused"
        if isinstance(cur, socket.gaierror):
            return "dns"
        cur = cur.__cause__ or cur.__context__
    return "error"


async def probe(
    client: httpx.AsyncClient,
    throttle: Throttle,
    base: str,
    path: str,
    timeout: int = 20,
) -> ProbeResult:
    """Throttled GET returning status + Location (body not read), or why no response
    came back (`failure`). Never raises."""
    async with throttle:
        try:
            async with client.stream("GET", base + path, timeout=timeout) as r:
                return {
                    "status": r.status_code,
                    "location": r.headers.get("location", ""),
                    "failure": "",
                }
        except (httpx.HTTPError, OSError) as e:
            return {"status": None, "location": "", "failure": _failure_kind(e)}


async def get_text(
    client: httpx.AsyncClient,
    throttle: Throttle,
    base: str,
    path: str,
    max_bytes: int,
    timeout: int = 20,
) -> str | None:
    """Throttled GET of a text body, reading at most `max_bytes` (streamed, so an
    oversized body is never fully downloaded). None on non-200 or error. Never raises."""
    async with throttle:
        try:
            async with client.stream("GET", base + path, timeout=timeout) as r:
                if r.status_code != 200:
                    return None
                buf = bytearray()
                async for part in r.aiter_bytes():
                    buf += part
                    if len(buf) >= max_bytes:
                        break
                return bytes(buf[:max_bytes]).decode(r.encoding or "utf-8", errors="replace")
        except (httpx.HTTPError, OSError):
            return None


def output_dir(scope: Scope) -> Path:
    """Where results/ and inventory/ live: the scope file's directory, or
    `[output].dir` resolved against it (absolute paths used as-is)."""
    base = scope_path().resolve().parent
    cfg = scope.get("output")
    override = cfg.get("dir") if cfg is not None else None
    return (base / override).resolve() if override else base


def results_dir(scope: Scope) -> Path:
    return output_dir(scope) / "results"


def inventory_file(scope: Scope) -> Path:
    return output_dir(scope) / "inventory" / "api_endpoints.json"


def load_endpoints(scope: Scope) -> list[dict[str, str]]:
    raw = json.loads(inventory_file(scope).read_text())
    return cast("list[dict[str, str]]", raw)


def write_jsonl(scope: Scope, name: str, rows: Sequence[Mapping[str, object]]) -> Path:
    out = results_dir(scope) / name
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    return out
