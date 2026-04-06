#!/usr/bin/env bash
set -euo pipefail

if ! command -v rg >/dev/null 2>&1; then
  echo "ripgrep (rg) is required to run validate-milestone-b.sh" >&2
  exit 1
fi

if ! command -v node >/dev/null 2>&1; then
  echo "node is required to run validate-milestone-b.sh" >&2
  exit 1
fi

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
FORBIDDEN_TOKEN="authorized_runtime""_handoff_envelope"

required_files=(
  "$ROOT/adapters/openclaw/bridge-shared-alignment.mjs"
  "$ROOT/adapters/openclaw/openclaw-host-handoff-backbone.mjs"
  "$ROOT/ingress/host-ingress-normalizer.mjs"
  "$ROOT/auth-linkage/ingress-identity-envelope-backbone.mjs"
  "$ROOT/auth-linkage/gate0-enforcement-backbone.mjs"
  "$ROOT/auth-linkage/authorized-session-link-backbone.mjs"
  "$ROOT/runtime-handoff/runtime-request-envelope-backbone.mjs"
  "$ROOT/dispatch/host-dispatch-handoff-backbone.mjs"
  "$ROOT/diagnostics/host-trace-backbone.mjs"
  "$ROOT/tests/milestone-b-auth-linkage.test.mjs"
)

for file in "${required_files[@]}"; do
  if [[ ! -f "$file" ]]; then
    echo "missing required file: $file" >&2
    exit 1
  fi
done

"$ROOT/scripts/validate-milestone-a.sh"

if rg -n "$FORBIDDEN_TOKEN" "$ROOT" --glob '!**/validate-milestone-a.sh' --glob '!**/validate-milestone-b.sh' >/dev/null 2>&1; then
  echo "forbidden legacy handoff alias found inside bridge milestone B files" >&2
  exit 1
fi

for token in host_ingress_envelope tool_publication_manifest host_dispatch_result host_trace_event; do
  if rg -n "$token.*(shared primary contract|shared canonical|canonical handoff)" -i "$ROOT" --glob '!**/validate-milestone-a.sh' --glob '!**/validate-milestone-b.sh' >/dev/null 2>&1; then
    echo "bridge local object leaked into shared canonical wording: $token" >&2
    exit 1
  fi
done

if ! rg -n 'runtime_request_envelope' "$ROOT/runtime-handoff" >/dev/null 2>&1; then
  echo "runtime_request_envelope backbone usage missing in runtime-handoff" >&2
  exit 1
fi

node --test "$ROOT/tests/milestone-b-auth-linkage.test.mjs"

echo "openclaw-host-bridge milestone B validation passed"
