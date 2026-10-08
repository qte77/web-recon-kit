"""Tests for lib.inventory's JS-bundle path-mining logic (pure, no network)."""
from lib.inventory import chunk_urls, crawl, endpoints, harvest_paths, script_urls

HOST = "example.test"
PAGE = "https://example.test/app/"


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


# --- static crawl (#56): entry HTML -> script tags -> code-split chunks ----------


def test_script_urls_resolves_scripts_and_modulepreloads_on_host_only() -> None:
    html = (
        '<script src="/assets/index.js"></script>'
        '<script src="main.js" type="module"></script>'
        '<link rel="modulepreload" href="/assets/vendor.js">'
        '<link rel="stylesheet" href="/assets/app.css">'
        '<script src="https://cdn.other.test/lib.js"></script>'
        "<script>inline()</script>"
        '<script src="/assets/index.js"></script>'
    )
    assert script_urls(html, PAGE, HOST) == [
        "https://example.test/assets/index.js",
        "https://example.test/app/main.js",
        "https://example.test/assets/vendor.js",
    ]


def test_chunk_urls_resolves_imports_against_the_fetching_chunk() -> None:
    js = (
        'const a=()=>import("./a.js");import{b}from"../shared/b.js";'
        "const c=import('./c.mjs');const d=\"/assets/d.js\";"
        'const e=import("https://cdn.other.test/e.js");const f="./not-js.css"'
    )
    chunk = "https://example.test/assets/js/index.js"
    assert chunk_urls(js, chunk, HOST) == [
        "https://example.test/assets/js/a.js",
        "https://example.test/assets/shared/b.js",
        "https://example.test/assets/js/c.mjs",
        "https://example.test/assets/d.js",
    ]


_SITE = {
    "https://example.test/assets/index.js": 'import("./mid.js");fetch("/api/root")',
    "https://example.test/assets/mid.js": 'import("./leaf.js");import("./index.js")',
    "https://example.test/assets/leaf.js": 'fetch("/api/leaf/items")',
}


async def test_crawl_reaches_three_level_leaf_without_refetching() -> None:
    fetched: list[str] = []

    async def fetch(url: str) -> str | None:
        fetched.append(url)
        return _SITE.get(url)

    html = '<script src="/assets/index.js"></script>'
    chunks = await crawl(fetch, html, "https://example.test/", HOST, max_chunks=100)

    assert list(chunks) == list(_SITE)
    assert fetched == list(_SITE)  # mid.js re-imports index.js: no second fetch
    assert harvest_paths(chunks, ("/api/",)) == ["/api/leaf/items", "/api/root"]


async def test_crawl_stops_at_chunk_cap() -> None:
    async def fetch(url: str) -> str | None:
        n = int(url.rsplit("/", 1)[1].removesuffix(".js"))
        return f'import("./{n + 1}.js")'

    chunks = await crawl(fetch, '<script src="/0.js"></script>', PAGE, HOST, max_chunks=5)
    assert len(chunks) == 5


async def test_crawl_never_fetches_off_host_and_keeps_failed_fetches_empty() -> None:
    fetched: list[str] = []

    async def fetch(url: str) -> str | None:
        fetched.append(url)
        return None

    html = (
        '<script src="https://cdn.other.test/x.js"></script>'
        # Substring look-alikes of the host must not pass the filter either.
        '<script src="https://example.test.evil.test/y.js"></script>'
        '<script src="https://evil.test/z.js?example.test"></script>'
        '<script src="/a.js"></script>'
    )
    chunks = await crawl(fetch, html, PAGE, HOST, max_chunks=10)
    assert fetched == ["https://example.test/a.js"]
    assert chunks == {"https://example.test/a.js": ""}


def test_endpoints_tags_source_and_appends_unseen_seeds() -> None:
    assert endpoints(["/api/a/x"], "static-crawl", ["/api/a/x", "/api/b"]) == [
        {"path": "/api/a/x", "module": "a", "source": "static-crawl"},
        {"path": "/api/b", "module": "b", "source": "seed"},
    ]
