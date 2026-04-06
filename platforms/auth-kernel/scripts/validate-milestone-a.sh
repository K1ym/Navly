#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
legacy_token="escalation""_required"

required_dirs=(
  contracts
  policy-catalog
  ingress-evidence
  actor-registry
  bindings
  decision
  governance
  serving
  migration
  scripts
  tests
)

for dir in "${required_dirs[@]}"; do
  if [[ ! -d "$ROOT/$dir" ]]; then
    echo "missing required directory: $dir" >&2
    exit 1
  fi
done

required_files=(
  "$ROOT/policy-catalog/actor-type-vocabulary.seed.yaml"
  "$ROOT/policy-catalog/role-catalog.seed.yaml"
  "$ROOT/policy-catalog/scope-taxonomy.seed.yaml"
  "$ROOT/policy-catalog/capability-vocabulary.seed.yaml"
  "$ROOT/policy-catalog/access-decision-status.alignment.yaml"
  "$ROOT/policy-catalog/decision-reason-taxonomy.seed.yaml"
  "$ROOT/policy-catalog/restriction-taxonomy.seed.yaml"
  "$ROOT/policy-catalog/obligation-taxonomy.seed.yaml"
)

for file in "${required_files[@]}"; do
  if [[ ! -f "$file" ]]; then
    echo "missing required file: $file" >&2
    exit 1
  fi
done

if rg -n "$legacy_token" "$ROOT" >/dev/null 2>&1; then
  echo "retired legacy escalation alias is forbidden inside platforms/auth-kernel" >&2
  exit 1
fi

if ! rg -n "capability_id: navly\." "$ROOT/policy-catalog/capability-vocabulary.seed.yaml" >/dev/null 2>&1; then
  echo "capability vocabulary seed must use namespaced capability_id" >&2
  exit 1
fi

echo "auth-kernel milestone A validation passed"
