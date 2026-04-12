import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { assertMatchesSharedPattern, sharedPatterns } from '../contracts/shared-contract-alignment.mjs';
import { mergeArrayByKey, readOptionalOverrideSeed } from '../local-overrides/seed-override-loader.mjs';

const moduleDir = path.dirname(fileURLToPath(import.meta.url));

function readJsonSeed(fileName) {
  return JSON.parse(fs.readFileSync(path.join(moduleDir, fileName), 'utf8'));
}

function aliasLookupKey(aliasNamespace, aliasValue) {
  return `${aliasNamespace}:${aliasValue}`;
}

export function loadActorRegistryBackbone() {
  const actorRegistrySeed = readJsonSeed('actor-registry.seed.json');
  const identityAliasRegistrySeed = readJsonSeed('identity-alias-registry.seed.json');
  const actorRegistryOverride = readOptionalOverrideSeed('actor-registry.override.json');
  const identityAliasRegistryOverride = readOptionalOverrideSeed('identity-alias-registry.override.json');

  const actors = mergeArrayByKey(
    actorRegistrySeed.actors ?? [],
    actorRegistryOverride?.actors ?? [],
    (entry) => entry.actor_ref,
  );
  const aliases = mergeArrayByKey(
    identityAliasRegistrySeed.aliases ?? [],
    identityAliasRegistryOverride?.aliases ?? [],
    (entry) => `${entry.alias_namespace}:${entry.alias_value}`,
  );

  const actorsByRef = new Map();
  for (const actor of actors) {
    assertMatchesSharedPattern('actor_ref', actor.actor_ref, sharedPatterns.actorRef);
    assertMatchesSharedPattern('tenant_ref', actor.tenant_ref, sharedPatterns.tenantRef);
    actorsByRef.set(actor.actor_ref, actor);
  }

  const aliasLookup = new Map();
  for (const alias of aliases) {
    const key = aliasLookupKey(alias.alias_namespace, alias.alias_value);
    const existing = aliasLookup.get(key) ?? [];
    existing.push(alias);
    aliasLookup.set(key, existing);
  }

  return {
    actorsByRef,
    aliases,
    aliasLookup,
  };
}

export function resolveActorFromIngress({ ingressEvidence, actorRegistryBackbone = loadActorRegistryBackbone() }) {
  const aliasMatches = [];

  for (const evidence of ingressEvidence.peer_identity_evidence ?? []) {
    const lookupKey = aliasLookupKey(evidence.alias_namespace, evidence.alias_value);
    aliasMatches.push(...(actorRegistryBackbone.aliasLookup.get(lookupKey) ?? []));
  }

  const uniqueActorRefs = [...new Set(aliasMatches.map((match) => match.actor_ref))];

  if (uniqueActorRefs.length === 0) {
    return {
      resolution_status: 'unknown',
      reason_codes: ['actor_unresolved'],
      matched_aliases: [],
    };
  }

  if (uniqueActorRefs.length > 1) {
    return {
      resolution_status: 'ambiguous',
      reason_codes: ['actor_ambiguous'],
      matched_aliases: aliasMatches,
    };
  }

  const actorRef = uniqueActorRefs[0];
  const actorRecord = actorRegistryBackbone.actorsByRef.get(actorRef);

  if (!actorRecord) {
    return {
      resolution_status: 'unknown',
      reason_codes: ['actor_unresolved'],
      matched_aliases: aliasMatches,
    };
  }

  if (actorRecord.lifecycle_state !== 'active') {
    return {
      resolution_status: 'inactive',
      actor_ref: actorRecord.actor_ref,
      actor_type: actorRecord.actor_type,
      lifecycle_state: actorRecord.lifecycle_state,
      tenant_ref: actorRecord.tenant_ref,
      reason_codes: ['actor_inactive'],
      matched_aliases: aliasMatches,
    };
  }

  return {
    resolution_status: 'resolved',
    actor_ref: actorRecord.actor_ref,
    actor_type: actorRecord.actor_type,
    lifecycle_state: actorRecord.lifecycle_state,
    tenant_ref: actorRecord.tenant_ref,
    reason_codes: [],
    matched_aliases: aliasMatches,
  };
}
