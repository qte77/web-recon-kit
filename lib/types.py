"""Shared typed schemas for the assessment harness (mypy --strict clean)."""
from __future__ import annotations

from typing import Literal, NotRequired, TypedDict

Verdict = Literal["GATED", "METHOD-405", "REVIEW"]


class IdentitySpec(TypedDict):
    """An identity as declared in scope.toml."""

    env: str
    role: str
    workspace: str


class ResolvedIdentity(IdentitySpec):
    """An identity with its token resolved from the environment."""

    token: str
    available: bool


class RateCfg(TypedDict):
    max_concurrency: int
    per_host_delay_ms: int


class SafetyCfg(TypedDict):
    methods: list[str]


class BolaCollector(TypedDict):
    kind: str
    list_path: str
    collection_key: str
    probe_template: str


class ReconCfg(TypedDict):
    routes: NotRequired[list[str]]
    cron_prefix: NotRequired[str]


class AuthMatrixCfg(TypedDict):
    public_ok: NotRequired[list[str]]


class BflaCfg(TypedDict):
    admin_prefixes: NotRequired[list[str]]


class BolaCfg(TypedDict):
    collectors: NotRequired[list[BolaCollector]]


class Scope(TypedDict):
    base_url: str
    identities: dict[str, IdentitySpec]
    rate: RateCfg
    safety: SafetyCfg
    recon: NotRequired[ReconCfg]
    authmatrix: NotRequired[AuthMatrixCfg]
    bfla: NotRequired[BflaCfg]
    bola: NotRequired[BolaCfg]


class GetResult(TypedDict):
    status: int | None
    content_type: str
    body: str
    location: str


class Endpoint(TypedDict):
    path: str
    module: str


class MatrixRow(TypedDict):
    path: str
    module: str
    identity: str
    status: int | None
    content_type: str


class CronRow(TypedDict):
    path: str
    get_noauth_status: int | None
    verdict: str


class BolaRow(TypedDict):
    kind: str
    resource_id: str
    probe_path: str
    owner_status: int | None
    tenant_b_status: int | None
    leak: bool


class BflaRow(TypedDict):
    path: str
    owner_status: int | None
    lowrole_status: int | None
    noauth_status: int | None
    escalation: bool
