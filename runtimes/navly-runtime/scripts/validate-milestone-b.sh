#!/usr/bin/env bash
set -euo pipefail

if ! command -v node >/dev/null 2>&1; then
  echo "node is required to run validate-milestone-b.sh" >&2
  exit 1
fi

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

required_files=(
  "$ROOT/README.md"
  "$ROOT/contracts/shared-contract-alignment.mjs"
  "$ROOT/ingress/runtime-ingress-backbone.mjs"
  "$ROOT/routing/capability-route-backbone.mjs"
  "$ROOT/routing/capability-route-registry.seed.json"
  "$ROOT/execution/guarded-execution-backbone.mjs"
  "$ROOT/execution/runtime-chain-backbone.mjs"
  "$ROOT/answering/runtime-result-backbone.mjs"
  "$ROOT/outcome/runtime-outcome-event-backbone.mjs"
  "$ROOT/scripts/validate-milestone-a.sh"
  "$ROOT/tests/milestone-b-guarded-execution.test.mjs"
)

for file in "${required_files[@]}"; do
  if [[ ! -f "$file" ]]; then
    echo "missing required milestone B file: $file" >&2
    exit 1
  fi
done

bash "$ROOT/scripts/validate-milestone-a.sh"

node - "$ROOT" <<'NODE'
const fs = require('node:fs');
const path = require('node:path');

const root = process.argv[2];
const routeRegistryPath = path.join(root, 'routing', 'capability-route-registry.seed.json');
const routeRegistry = JSON.parse(fs.readFileSync(routeRegistryPath, 'utf8'));

if (routeRegistry.status !== 'milestone_b_backbone') {
  throw new Error(`route registry status must be milestone_b_backbone, got ${routeRegistry.status}`);
}

const expectedCapabilityId = 'navly.store.daily_overview';
const expectedServiceObjectId = 'navly.service.store.daily_overview';

const entry = (routeRegistry.entries ?? []).find((item) => item.capability_id === expectedCapabilityId);
if (!entry) {
  throw new Error(`route registry must include ${expectedCapabilityId}`);
}
if (entry.default_service_object_id !== expectedServiceObjectId) {
  throw new Error(`default_service_object_id must be ${expectedServiceObjectId}`);
}

const fallback = routeRegistry.default_fallback ?? {};
if (fallback.result_status !== 'fallback') {
  throw new Error(`route fallback result_status must be fallback, got ${fallback.result_status}`);
}
if (fallback.fallback_capability_id !== 'navly.system.capability_explanation') {
  throw new Error('fallback_capability_id drift detected');
}
if (fallback.fallback_service_object_id !== 'navly.service.system.capability_explanation') {
  throw new Error('fallback_service_object_id drift detected');
}

const sharedRuntimeStatusPath = path.join(root, '..', '..', 'shared', 'contracts', 'enums', 'runtime_result_status.schema.json');
const sharedRuntimeStatus = JSON.parse(fs.readFileSync(sharedRuntimeStatusPath, 'utf8')).enum;
const expectedStatus = ['answered', 'fallback', 'escalated', 'rejected', 'runtime_error'];
if (JSON.stringify(sharedRuntimeStatus) !== JSON.stringify(expectedStatus)) {
  throw new Error(`shared runtime_result_status enum drift: ${JSON.stringify(sharedRuntimeStatus)}`);
}
NODE

node --test "$ROOT/tests/milestone-b-guarded-execution.test.mjs"

echo "runtime milestone B validation passed"
