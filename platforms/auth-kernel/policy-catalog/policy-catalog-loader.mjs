import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { assertCapabilityId, sharedEnums } from '../contracts/shared-contract-alignment.mjs';

const moduleDir = path.dirname(fileURLToPath(import.meta.url));

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
  const actorTypes = readJsonSeed('actor-type-vocabulary.seed.json');
  const roles = readJsonSeed('role-catalog.seed.json');
  const scopeTaxonomy = readJsonSeed('scope-taxonomy.seed.json');
  const capabilityVocabulary = readJsonSeed('capability-vocabulary.seed.json');
  const decisionReasons = readJsonSeed('decision-reason-taxonomy.seed.json');
  const restrictions = readJsonSeed('restriction-taxonomy.seed.json');
  const obligations = readJsonSeed('obligation-taxonomy.seed.json');
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
