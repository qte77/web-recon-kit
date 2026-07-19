# Glossary

Abbreviations used across web-recon-kit, its runners, and generated reports. Grouped by theme;
each is expanded and briefly defined.

## Authorization & access-control flaws

- **IDOR** — Insecure Direct Object Reference. A request references an object (by id, path, …)
  the caller shouldn't be able to reach, and the server returns it anyway.
- **BOLA** — Broken Object-Level Authorization. The API-specific name for IDOR: object-level
  access isn't enforced, so one tenant/user can read another's resource. (OWASP API #1.)
- **BFLA** — Broken Function-Level Authorization. A lower-privileged identity can invoke an
  admin/privileged *function* (endpoint) it shouldn't. (OWASP API #5.)
- **RBAC** — Role-Based Access Control. Permissions granted via roles rather than per-user.
- **PoLP** — Principle of Least Privilege. Grant only the access strictly required.

## Identity & authentication

- **SSO** — Single Sign-On. One identity provider authenticates a user across apps.
- **SAML** — Security Assertion Markup Language. XML-based SSO/federation protocol.
- **OIDC** — OpenID Connect. Identity layer on top of OAuth 2.0.
- **MFA** — Multi-Factor Authentication. More than one factor (e.g. password + code).
- **TOTP** — Time-based One-Time Password. The rotating 6-digit code form of MFA.
- **JWT** — JSON Web Token. Signed, self-contained token often used for sessions.
- **CSRF** — Cross-Site Request Forgery. Tricking a browser into sending an authed request;
  mitigated by origin/token checks.
- **SCIM** — System for Cross-domain Identity Management. Standard API for provisioning users
  and groups from an identity provider.
- **VAPID** — Voluntary Application Server Identification. The public/private keypair scheme for
  Web Push; the *public* key is meant to be exposed.

## Testing, scanning & disclosure

- **SAST** — Static Application Security Testing. Analyzes source/code (e.g. CodeQL).
- **DAST** — Dynamic Application Security Testing. Probes a running app.
- **SCA** — Software Composition Analysis. Scans dependencies for known vulnerabilities
  (e.g. pip-audit).
- **CVE** — Common Vulnerabilities and Exposures. A catalogued, identified vulnerability.
- **OWASP** — Open Worldwide Application Security Project. Publishes the Top 10 / API Top 10.
- **DoS** — Denial of Service. Overwhelming a target; explicitly out of scope for this kit.
- **CTF** — Capture The Flag. Sanctioned security competition (a valid authorization context).
- **PII** — Personally Identifiable Information.

## Web platform & protocols

- **API** — Application Programming Interface. Here, the target's HTTP endpoints.
- **SPA** — Single-Page Application. Client-rendered app; the initial HTML is a shell.
- **RSC** — React Server Components. Next.js server-rendering mechanism.
- **MCP** — Model Context Protocol. Standard for connecting AI agents/tools to a server.
- **TLS** / **JA3** — Transport Layer Security / a TLS-client fingerprint (used by the browser
  tier to look like a real client).
- **URL** / **HTTP** — Uniform Resource Locator / HyperText Transfer Protocol.

## Tooling & delivery

- **CI** — Continuous Integration. Automated build/test on push/PR (here, GitHub Actions).
- **GHA** — GitHub Actions.
- **GHAS** — GitHub Advanced Security. Enables code scanning (CodeQL SARIF) on private repos.
- **PR** — Pull Request.
- **SHA** — the full commit hash actions are pinned to (supply-chain hardening).
- **SARIF** — Static Analysis Results Interchange Format. CodeQL's output format.
- **uv** — the Python package/venv manager used here.
- **env-borrow** — running a tool from another repo's virtualenv via `uv run --directory <repo>`,
  so its heavy deps never enter this project's lockfile (a polyfetch-scrape contract; see its
  `USING.md`). web-recon-kit no longer uses it — polyfetch is now the optional `browser` extra
  (see [polyfetch integration](polyfetch-integration.md)).

[poly]: https://github.com/qte77/polyfetch-scrape
