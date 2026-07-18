#!/usr/bin/env bash
# (2) Property-based API fuzzing driven by an OpenAPI 3.x spec.
#
# The target's spec is often repo-only / not served publicly. Obtain it, then:
#   BASE_URL=https://target.example.com RECON_API_KEY=... SPEC=/path/openapi.yaml \
#     bash runners/r2_schemathesis.sh
#
# Mutating methods are excluded by default (safety); flip EXCLUDE_MUTATING=0 only
# against a disposable environment. Tune flags to your installed schemathesis version.
set -euo pipefail
: "${SPEC:?set SPEC=/path/to/openapi.yaml}"
: "${BASE_URL:?set BASE_URL=https://target.example.com}"
# Provide the API key via RECON_API_KEY, or point ENV at a file to source it from.
[ -n "${ENV:-}" ] && { set -a; . "$ENV"; set +a; }
: "${RECON_API_KEY:?set RECON_API_KEY (or source it via ENV=/path/.env)}"

EXCLUDE=()
if [ "${EXCLUDE_MUTATING:-1}" = "1" ]; then
  EXCLUDE=(--exclude-method DELETE --exclude-method POST --exclude-method PATCH --exclude-method PUT)
fi

uvx schemathesis run "$SPEC" \
  --base-url "$BASE_URL" \
  --header "Authorization: Bearer ${RECON_API_KEY}" \
  --checks all \
  --rate-limit "${RATE:-5/s}" \
  --max-examples "${MAX:-30}" \
  "${EXCLUDE[@]}"
