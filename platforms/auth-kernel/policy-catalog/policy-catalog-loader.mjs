import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { assertCapabilityId, sharedEnums } from '../contracts/shared-contract-alignment.mjs';

const moduleDir = path.dirname(fileURLToPath(import.meta.url));

function parseScalar(rawValue) {
  const value = rawValue.trim();
  if (value === 'true') return true;
  if (value === 'false') return false;
  if (/^-?\d+$/.test(value)) return Number(value);
  if ((value.startsWith('"') && value.endsWith('"')) || (value.startsWith("'") && value.endsWith("'"))) {
    return value.slice(1, -1);
  }
  return value;
}

export function parseSimpleSeedYaml(sourceText) {
  const result = {};
  let activeListKey = null;
  let activeItem = null;

  for (const rawLine of sourceText.split(/\r?\n/)) {
    if (!rawLine.trim() || rawLine.trim().startsWith('#')) {
      continue;
    }

    const indent = rawLine.match(/^ */)[0].length;
    const line = rawLine.trim();

    if (indent === 0) {
      const [rawKey, ...rawRest] = line.split(':');
      const key = rawKey.trim();
      const rest = rawRest.join(':').trim();
      if (!rest) {
        result[key] = [];
        activeListKey = key;
        activeItem = null;
      } else {
        result[key] = parseScalar(rest);
        activeListKey = null;
        activeItem = null;
      }
      continue;
    }

    if (activeListKey && indent === 2 && line.startsWith('- ')) {
      activeItem = {};
      result[activeListKey].push(activeItem);
      const inline = line.slice(2).trim();
      if (inline) {
        const [rawKey, ...rawRest] = inline.split(':');
        activeItem[rawKey.trim()] = parseScalar(rawRest.join(':').trim());
      }
      continue;
    }

    if (activeListKey && activeItem && indent >= 4) {
      const [rawKey, ...rawRest] = line.split(':');
      activeItem[rawKey.trim()] = parseScalar(rawRest.join(':').trim());
    }
  }

  return result;
}

function readYamlSeed(fileName) {
  return parseSimpleSeedYaml(fs.readFileSync(path.join(moduleDir, fileName), 'utf8'));
}

function readJsonSeed(fileName) {
  return JSON.parse(fs.readFileSync(path.join(moduleDir, fileName), 'utf8'));
}

export function assertCatalogCodes(label, codes, allowedCodes) {
  const allowedSet = new Set(allowedCodes);
  for (const code of codes ?? []) {
    if (!allowedSet.has(code)) {
      throw new Error(`${label} contains code outside policy catalog: ${code}`);
    }
  }
  return codes;
}

export function loadPolicyCatalog() {
  const actorTypes = readYamlSeed('actor-type-vocabulary.seed.yaml');
  const roles = readYamlSeed('role-catalog.seed.yaml');
  const scopeTaxonomy = readYamlSeed('scope-taxonomy.seed.yaml');
  const capabilityVocabulary = readYamlSeed('capability-vocabulary.seed.yaml');
  const decisionReasons = readYamlSeed('decision-reason-taxonomy.seed.yaml');
  const restrictions = readYamlSeed('restriction-taxonomy.seed.yaml');
  const obligations = readYamlSeed('obligation-taxonomy.seed.yaml');
  const capabilityGrantProfile = readJsonSeed('capability-grant-profile.seed.json');

  const capabilityById = new Map();
  for (const capability of capabilityVocabulary.capabilities ?? []) {
    assertCapabilityId(capability.capability_id);
    capabilityById.set(capability.capability_id, capability);
  }

  const grantProfileByRoleId = new Map();
  for (const grantProfile of capabilityGrantProfile.grant_profiles ?? []) {
    for (const capabilityId of grantProfile.capability_ids ?? []) {
      assertCapabilityId(capabilityId);
      if (!capabilityById.has(capabilityId)) {
        throw new Error(`capability grant profile references unknown capability_id ${capabilityId}`);
      }
    }
    grantProfileByRoleId.set(grantProfile.role_id, [...(grantProfile.capability_ids ?? [])]);
  }

  for (const scopeEntry of scopeTaxonomy.scope_kinds ?? []) {
    if (!sharedEnums.scopeKind.includes(scopeEntry.scope_kind)) {
      throw new Error(`scope taxonomy contains unknown shared scope kind ${scopeEntry.scope_kind}`);
    }
  }

  return {
    actorTypes: actorTypes.actor_types ?? [],
    roles: roles.roles ?? [],
    scopeKinds: scopeTaxonomy.scope_kinds ?? [],
    capabilities: capabilityVocabulary.capabilities ?? [],
    capabilityById,
    decisionReasonCodes: (decisionReasons.reason_codes ?? []).map((entry) => entry.reason_code),
    restrictionCodes: (restrictions.restriction_codes ?? []).map((entry) => entry.restriction_code),
    obligationCodes: (obligations.obligation_codes ?? []).map((entry) => entry.obligation_code),
    grantProfileByRoleId,
  };
}
