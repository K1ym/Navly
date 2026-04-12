import fs from 'node:fs';
import path from 'node:path';

const DEFAULT_OVERRIDE_DIR = '/etc/navly/auth-kernel';

function normalizeOptionalString(value) {
  if (value === undefined || value === null) {
    return null;
  }
  const normalized = String(value).trim();
  return normalized ? normalized : null;
}

export function resolveAuthKernelOverrideDir(env = process.env) {
  return normalizeOptionalString(env.NAVLY_AUTH_KERNEL_OVERRIDE_DIR) ?? DEFAULT_OVERRIDE_DIR;
}

export function readOptionalOverrideSeed(fileName, env = process.env) {
  const candidatePath = path.join(resolveAuthKernelOverrideDir(env), fileName);
  if (!fs.existsSync(candidatePath)) {
    return null;
  }
  return JSON.parse(fs.readFileSync(candidatePath, 'utf8'));
}

export function mergeArrayByKey(baseEntries, overrideEntries, keyBuilder) {
  const registry = new Map();
  for (const entry of baseEntries ?? []) {
    registry.set(keyBuilder(entry), entry);
  }
  for (const entry of overrideEntries ?? []) {
    registry.set(keyBuilder(entry), entry);
  }
  return [...registry.values()];
}
