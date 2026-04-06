#!/usr/bin/env bash
set -euo pipefail

if ! command -v rg >/dev/null 2>&1; then
  echo "ripgrep (rg) is required to run validate-milestone-a.sh" >&2
  exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 is required to run validate-milestone-a.sh" >&2
  exit 1
fi

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SHARED_ROOT="$ROOT/../../shared/contracts"

required_dirs=(
  contracts
  ingress
  routing
  execution
  answering
  outcome
  adapters
  migration
  scripts
  tests
  docs
)

for dir in "${required_dirs[@]}"; do
  if [[ ! -d "$ROOT/$dir" ]]; then
    echo "missing required directory: $dir" >&2
    exit 1
  fi
done

required_files=(
  "$ROOT/README.md"
  "$ROOT/contracts/runtime-shared-contract-consumption.manifest.json"
  "$ROOT/routing/capability-route-registry.seed.json"
  "$ROOT/scripts/validate-milestone-a.sh"
)

for file in "${required_files[@]}"; do
  if [[ ! -f "$file" ]]; then
    echo "missing required file: $file" >&2
    exit 1
  fi
done

python3 - "$ROOT" "$SHARED_ROOT" <<'PY'
import json
import pathlib
import re
import sys

root = pathlib.Path(sys.argv[1])
shared_root = pathlib.Path(sys.argv[2])

manifest_path = root / "contracts" / "runtime-shared-contract-consumption.manifest.json"
registry_path = root / "routing" / "capability-route-registry.seed.json"
shared_status_path = shared_root / "enums" / "runtime_result_status.schema.json"

manifest = json.loads(manifest_path.read_text())
registry = json.loads(registry_path.read_text())
shared_status = json.loads(shared_status_path.read_text())

required_contracts = {
    "access_context_envelope",
    "access_decision",
    "capability_readiness_query",
    "capability_readiness_response",
    "theme_service_query",
    "theme_service_response",
    "runtime_request_envelope",
    "runtime_result_envelope",
    "runtime_outcome_event",
}

consumed_names = {item["name"] for item in manifest.get("consumes", [])}
if consumed_names != required_contracts:
    missing = sorted(required_contracts - consumed_names)
    extra = sorted(consumed_names - required_contracts)
    raise SystemExit(
        f"runtime shared contract manifest mismatch; missing={missing}, extra={extra}"
    )

for item in manifest.get("consumes", []):
    path = item.get("path", "")
    if not path.startswith("shared/contracts/"):
        raise SystemExit(f"shared contract path must stay under shared/contracts: {path}")

enum_values = shared_status.get("enum", [])
expected_enum = ["answered", "fallback", "escalated", "rejected", "runtime_error"]
if enum_values != expected_enum:
    raise SystemExit(
        "shared runtime_result_status enum drift detected; expected "
        f"{expected_enum}, got {enum_values}"
    )

capability_pattern = re.compile(r"^navly\.[a-z0-9_]+\.[a-z0-9_]+$")
service_pattern = re.compile(r"^navly\.service\.[a-z0-9_]+\.[a-z0-9_]+$")
entries = registry.get("entries", [])
if not entries:
    raise SystemExit("capability route registry must contain at least one seed entry")

expected_route_strategy = "capability_first_then_service_object"
if registry.get("route_strategy") != expected_route_strategy:
    raise SystemExit(
        "capability route registry must freeze explicit route_strategy; expected "
        f"{expected_route_strategy}, got {registry.get('route_strategy')}"
    )

for idx, entry in enumerate(entries):
    capability_id = entry.get("capability_id", "")
    service_object_id = entry.get("default_service_object_id", "")
    if not capability_pattern.match(capability_id):
        raise SystemExit(
            f"route entry #{idx} capability_id is not namespaced canonical: {capability_id}"
        )
    if not service_pattern.match(service_object_id):
        raise SystemExit(
            f"route entry #{idx} default_service_object_id is not namespaced canonical: {service_object_id}"
        )

fallback = registry.get("default_fallback", {})
if fallback.get("result_status") not in expected_enum:
    raise SystemExit(
        "default_fallback.result_status must use frozen shared runtime_result_status enum"
    )
if fallback.get("result_status") != "fallback":
    raise SystemExit(
        "default_fallback.result_status must be fallback for unresolved route clarification flow"
    )
PY

scan_paths=(
  "$ROOT/contracts"
  "$ROOT/ingress"
  "$ROOT/routing"
  "$ROOT/execution"
  "$ROOT/answering"
  "$ROOT/outcome"
  "$ROOT/adapters"
  "$ROOT/migration"
  "$ROOT/tests"
)

forbidden_subject_pattern='endpoint|physical[ _-]?table|raw[ _-]?truth|raw-store|warehouse[ _-]?table|sql[ _-]?query'
if rg -q -i "$forbidden_subject_pattern" "${scan_paths[@]}"; then
  echo "runtime milestone A forbids endpoint/table/raw-truth-centric wording in runtime module artifacts" >&2
  rg -n -i "$forbidden_subject_pattern" "${scan_paths[@]}" >&2
  exit 1
fi

legacy_glue_pattern='query_glue|prompt_glue|legacy_glue|legacy_query|legacy_route|legacy_routing'
if rg -q -i "$legacy_glue_pattern" "${scan_paths[@]}"; then
  echo "legacy glue naming is forbidden in runtime milestone A artifacts" >&2
  rg -n -i "$legacy_glue_pattern" "${scan_paths[@]}" >&2
  exit 1
fi

if rg -n "title" "$ROOT/contracts" | rg -n "runtime_result_status" >/dev/null 2>&1; then
  echo "runtime_result_status must remain shared-owned; local enum title found in runtime contracts" >&2
  exit 1
fi

echo "runtime milestone A validation passed"
