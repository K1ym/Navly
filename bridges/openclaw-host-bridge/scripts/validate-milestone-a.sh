#!/usr/bin/env bash
set -euo pipefail

if ! command -v rg >/dev/null 2>&1; then
  echo "ripgrep (rg) is required to run validate-milestone-a.sh" >&2
  exit 1
fi

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
README_FILE="$ROOT/README.md"
FORBIDDEN_TOKEN="authorized_runtime""_handoff_envelope"

required_dirs=(
  adapters/openclaw
  ingress
  auth-linkage
  tool-publication
  runtime-handoff
  dispatch
  diagnostics
  migration
  scripts
  tests
  docs
)

required_files=(
  "$ROOT/README.md"
  "$ROOT/docs/README.md"
  "$ROOT/adapters/openclaw/README.md"
  "$ROOT/ingress/README.md"
  "$ROOT/ingress/host-ingress-envelope.placeholder.json"
  "$ROOT/auth-linkage/README.md"
  "$ROOT/tool-publication/README.md"
  "$ROOT/tool-publication/tool-publication-manifest.placeholder.json"
  "$ROOT/runtime-handoff/README.md"
  "$ROOT/dispatch/README.md"
  "$ROOT/dispatch/host-dispatch-result.placeholder.json"
  "$ROOT/diagnostics/README.md"
  "$ROOT/diagnostics/host-trace-event.placeholder.json"
  "$ROOT/migration/README.md"
  "$ROOT/scripts/README.md"
  "$ROOT/tests/README.md"
)

for dir in "${required_dirs[@]}"; do
  if [[ ! -d "$ROOT/$dir" ]]; then
    echo "missing required directory: $dir" >&2
    exit 1
  fi
done

for file in "${required_files[@]}"; do
  if [[ ! -f "$file" ]]; then
    echo "missing required file: $file" >&2
    exit 1
  fi
done

if rg -n "$FORBIDDEN_TOKEN" "$ROOT" --glob "!**/validate-milestone-a.sh" >/dev/null 2>&1; then
  echo "forbidden legacy handoff name found inside bridges/openclaw-host-bridge" >&2
  exit 1
fi

if ! rg -n 'runtime_request_envelope' "$ROOT" >/dev/null 2>&1; then
  echo "runtime_request_envelope must appear inside bridge milestone A skeleton" >&2
  exit 1
fi

if ! rg -n 'runtime_request_envelope.*唯一 canonical handoff' "$README_FILE" >/dev/null 2>&1; then
  echo "README must declare runtime_request_envelope as the only canonical handoff name" >&2
  exit 1
fi

for token in host_ingress_envelope tool_publication_manifest host_dispatch_result; do
  if ! rg -n "$token" "$README_FILE" >/dev/null 2>&1; then
    echo "README must list bridge local object: $token" >&2
    exit 1
  fi
done

for token in runtime_request_envelope runtime_result_envelope runtime_outcome_event; do
  if ! rg -n "$token" "$README_FILE" >/dev/null 2>&1; then
    echo "README must list shared interaction consumption object: $token" >&2
    exit 1
  fi
done

if rg -n '(host_ingress_envelope|tool_publication_manifest|host_dispatch_result).*(shared canonical|canonical handoff|shared primary contract)' -i "$ROOT" --glob "!**/validate-milestone-a.sh" >/dev/null 2>&1; then
  echo "bridge local objects must not be described as shared canonical contracts" >&2
  rg -n '(host_ingress_envelope|tool_publication_manifest|host_dispatch_result).*(shared canonical|canonical handoff|shared primary contract)' -i "$ROOT" --glob "!**/validate-milestone-a.sh" >&2
  exit 1
fi

if rg -n '(host_ingress_envelope|tool_publication_manifest|host_dispatch_result).*(shared/contracts/interaction)' -i "$ROOT" --glob "!**/validate-milestone-a.sh" >/dev/null 2>&1; then
  echo "bridge local objects must not point to shared/contracts/interaction as their owning location" >&2
  rg -n '(host_ingress_envelope|tool_publication_manifest|host_dispatch_result).*(shared/contracts/interaction)' -i "$ROOT" --glob "!**/validate-milestone-a.sh" >&2
  exit 1
fi

echo "openclaw-host-bridge milestone A validation passed"
