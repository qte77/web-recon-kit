# polyfetch-scrape integration (browser tier)

The **browser tier** — endpoint-inventory mining, gate classification, and per-route
screenshots — is built on **[polyfetch-scrape][poly]**. The **API tier**
(`authmatrix`, `cron`, `bola`, `bfla`, `report`) is plain `httpx` and does **not**
need polyfetch. See [Architecture](architecture.md#two-tiers) for the tier split.

## How web-recon-kit uses polyfetch

Both browser-tier runners import a single entry point — `polyfetch_scrape.render_session(url)` —
and drive headless Chromium through the `session.page` handle it yields:

- **`inventory/build_inventory.py` — JS-bundle mining.** Loads the target, then runs
  in-page JS to fetch every same-host `*.js` bundle and greps them for `/api/*` string
  literals, producing `inventory/api_endpoints.json`. This is static analysis of code the
  target already ships to browsers — **no API key required**.
- **`runners/r1_recon.py` — gate classification + screenshots.** Renders each route in
  `[recon].routes`, watches the document response, follows client-side redirects, captures
  console/network state, and writes a full-page screenshot per route to
  `results/screens/`.

### Gate classification

`r1_recon` distinguishes *where* a route is protected by comparing the requested route,
the document HTTP status, and the final (post-JS) URL:

| Gate | Meaning |
|---|---|
| `public` | no redirect, document returned `200` |
| `status-<code>` | no redirect, non-`200` document |
| `client-side-gate` | `200` document, then JS bounced to `/login` (protection is client-only — a smell) |
| `server-middleware-gate` | redirected before content (protected at the edge/middleware) |

A `client-side-gate` is the notable signal: the server served the page and the client
merely *hid* it, so the underlying data may still be reachable without the UI.

## Why polyfetch specifically

polyfetch wraps **patchright/Chromium** with a realistic TLS/[JA3](glossary.md#web-platform--protocols)
fingerprint, so the target sees a genuine browser client rather than a scripted one. That
matters for the browser tier because bundle mining and gate classification depend on the
target rendering and serving JS the way it does for real users. `render_session` gives a
context-managed page with the network/console hooks the runners rely on — reused rather than
rebuilt here (see polyfetch's `USING.md`).

## Install & run

polyfetch pulls heavy dependencies (patchright, curl_cffi), so it is an **optional
`browser` extra** — kept out of the API tier's install. It is a real dependency
(`git+https://github.com/qte77/polyfetch-scrape.git` in `pyproject.toml`), **not** an
env-borrowed sibling checkout, so no `POLY=/path` override or separate clone is needed.

```bash
make setup-browser    # uv sync --extra browser  +  uv run patchright install chromium (once)
make inventory        # (re)mine /api/* from JS bundles -> inventory/api_endpoints.json
make recon            # gate classification + screenshots -> results/recon.jsonl, results/screens/
```

Once `make setup-browser` has installed the extra into the project's own venv, the runners
resolve `import polyfetch_scrape` normally — no path plumbing. CI never installs the
`browser` extra (API-tier gates only), so the polyfetch import is exercised locally.

[poly]: https://github.com/qte77/polyfetch-scrape
