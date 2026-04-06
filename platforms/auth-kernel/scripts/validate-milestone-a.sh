#!/usr/bin/env bash
set -euo pipefail

if ! command -v rg >/dev/null 2>&1; then
  echo "ripgrep (rg) is required to run validate-milestone-a.sh" >&2
  exit 1
fi

if ! command -v node >/dev/null 2>&1; then
  echo "node is required to validate milestone A JSON seeds" >&2
  exit 1
fi

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
legacy_token="escalation""_required"
capability_seed="$ROOT/policy-catalog/capability-vocabulary.seed.json"

required_dirs=(
  docs
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
  "$ROOT/policy-catalog/actor-type-vocabulary.seed.json"
  "$ROOT/policy-catalog/role-catalog.seed.json"
  "$ROOT/policy-catalog/scope-taxonomy.seed.json"
  "$ROOT/policy-catalog/capability-vocabulary.seed.json"
  "$ROOT/policy-catalog/access-decision-status.alignment.json"
  "$ROOT/policy-catalog/decision-reason-taxonomy.seed.json"
  "$ROOT/policy-catalog/restriction-taxonomy.seed.json"
  "$ROOT/policy-catalog/obligation-taxonomy.seed.json"
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

node --input-type=module - "$capability_seed" <<'EOF'
import fs from 'node:fs';

const capabilitySeedPath = process.argv[2];
const capabilitySeed = JSON.parse(fs.readFileSync(capabilitySeedPath, 'utf8'));
const capabilities = capabilitySeed.capabilities;

if (!Array.isArray(capabilities) || capabilities.length === 0) {
  console.error('capability vocabulary seed must declare at least one capability_id');
  process.exit(1);
}

for (const capability of capabilities) {
  if (typeof capability.capability_id !== 'string' || !capability.capability_id.startsWith('navly.')) {
    console.error('all capability_id entries must use namespaced navly.* format');
    console.error(JSON.stringify(capability, null, 2));
    process.exit(1);
  }
}
EOF

echo "auth-kernel milestone A validation passed"
