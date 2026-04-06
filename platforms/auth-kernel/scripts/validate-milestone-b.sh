#!/usr/bin/env bash
set -euo pipefail

if ! command -v node >/dev/null 2>&1; then
  echo "node is required to run validate-milestone-b.sh" >&2
  exit 1
fi

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
legacy_token="escalation""_required"

required_files=(
  "$ROOT/contracts/contract-ownership.seed.json"
  "$ROOT/contracts/shared-contract-alignment.mjs"
  "$ROOT/policy-catalog/actor-type-vocabulary.seed.json"
  "$ROOT/policy-catalog/role-catalog.seed.json"
  "$ROOT/policy-catalog/scope-taxonomy.seed.json"
  "$ROOT/policy-catalog/capability-vocabulary.seed.json"
  "$ROOT/policy-catalog/access-decision-status.alignment.json"
  "$ROOT/policy-catalog/decision-reason-taxonomy.seed.json"
  "$ROOT/policy-catalog/restriction-taxonomy.seed.json"
  "$ROOT/policy-catalog/obligation-taxonomy.seed.json"
  "$ROOT/policy-catalog/policy-catalog-loader.mjs"
  "$ROOT/policy-catalog/capability-grant-profile.seed.json"
  "$ROOT/actor-registry/actor-registry.seed.json"
  "$ROOT/actor-registry/identity-alias-registry.seed.json"
  "$ROOT/actor-registry/identity-resolution-result.contract.seed.json"
  "$ROOT/actor-registry/actor-resolution-backbone.mjs"
  "$ROOT/bindings/role-binding.seed.json"
  "$ROOT/bindings/scope-binding.seed.json"
  "$ROOT/bindings/conversation-binding.seed.json"
  "$ROOT/bindings/binding-snapshot.contract.seed.json"
  "$ROOT/bindings/binding-backbone.mjs"
  "$ROOT/decision/gate0-result.contract.seed.json"
  "$ROOT/decision/access-decision-owner-view.contract.seed.json"
  "$ROOT/decision/gate0-backbone.mjs"
  "$ROOT/decision/capability-access-decision-backbone.mjs"
  "$ROOT/ingress-evidence/host-evidence-normalizer.mjs"
  "$ROOT/serving/access-context-envelope-backbone.mjs"
  "$ROOT/serving/access-chain-backbone.mjs"
  "$ROOT/tests/milestone-b-backbone.test.mjs"
)

for file in "${required_files[@]}"; do
  if [[ ! -f "$file" ]]; then
    echo "missing required milestone B file: $file" >&2
    exit 1
  fi
done

bash "$ROOT/scripts/validate-milestone-a.sh"

if rg -n "$legacy_token" "$ROOT" >/dev/null 2>&1; then
  echo "retired legacy escalation alias is forbidden inside platforms/auth-kernel" >&2
  exit 1
fi

node --test "$ROOT/tests/milestone-b-backbone.test.mjs"

echo "auth-kernel milestone B validation passed"
