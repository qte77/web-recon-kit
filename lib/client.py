"""Shared config + throttled async HTTP client (mypy --strict clean).

Only httpx (PEP 561-typed) + stdlib. Read-only GET/OPTIONS by design.
"""
from __future__ import annotations

import asyncio
import json
import os
import time
import tomllib
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import cast
from urllib.parse import urlparse

import httpx

from lib.types import BolaCollector, GetResult, ResolvedIdentity, Scope

ROOT: Path = Path(__file__).resolve().parent.parent


def load_scope() -> Scope:
    with (ROOT / "scope.toml").open("rb") as f:
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


def identities(scope: Scope) -> dict[str, ResolvedIdentity]:
    """Resolve each identity's bearer token from the environment."""
    out: dict[str, ResolvedIdentity] = {}
    for name, spec in scope["identities"].items():
        tok = os.environ.get(spec["env"], "")
        out[name] = {
            "env": spec["env"], "role": spec["role"], "workspace": spec["workspace"],
            "token": tok, "available": bool(tok),
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


def load_endpoints() -> list[dict[str, str]]:
    raw = json.loads((ROOT / "inventory" / "api_endpoints.json").read_text())
    return cast("list[dict[str, str]]", raw)


def write_jsonl(name: str, rows: Sequence[Mapping[str, object]]) -> Path:
    out = ROOT / "results" / name
    out.parent.mkdir(exist_ok=True)
    out.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    return out
