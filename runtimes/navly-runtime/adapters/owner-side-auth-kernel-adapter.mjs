import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { runMilestoneBAccessChain } from '../../../platforms/auth-kernel/serving/access-chain-backbone.mjs';

const moduleDir = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(moduleDir, '..', '..', '..');
const defaultAliasRegistryPath = path.join(
  repoRoot,
  'platforms',
  'auth-kernel',
  'actor-registry',
  'identity-alias-registry.seed.json',
);
const defaultPreferredAliasNamespaces = ['wecom_user_id', 'openclaw_host_account'];

function asNonEmptyString(value) {
  return typeof value === 'string' && value.trim().length > 0 ? value.trim() : null;
}

function normalizePeerIdentityEntry(entry) {
  if (!entry || typeof entry !== 'object') {
    return null;
  }

  const aliasNamespace = asNonEmptyString(entry.alias_namespace);
  const aliasValue = asNonEmptyString(entry.alias_value);
  if (!aliasNamespace || !aliasValue) {
    return null;
  }

  return {
    alias_namespace: aliasNamespace,
    alias_value: aliasValue,
  };
}

function readJson(filePath) {
  return JSON.parse(fs.readFileSync(filePath, 'utf8'));
}

function loadActorAliasLookup(aliasRegistryPath) {
  const aliases = readJson(aliasRegistryPath).aliases ?? [];
  const lookup = new Map();
  for (const alias of aliases) {
    const actorRef = asNonEmptyString(alias.actor_ref);
    const normalized = normalizePeerIdentityEntry(alias);
    if (!actorRef || !normalized) {
      continue;
    }

    const current = lookup.get(actorRef) ?? [];
    current.push(normalized);
    lookup.set(actorRef, current);
  }

  return lookup;
}

function pickAliasForActor(actorAliases, preferredAliasNamespaces) {
  if (!Array.isArray(actorAliases) || actorAliases.length === 0) {
    return null;
  }

  for (const namespace of preferredAliasNamespaces) {
    const match = actorAliases.find((entry) => entry.alias_namespace === namespace);
    if (match) {
      return match;
    }
  }

  return actorAliases[0];
}

function resolvePeerIdentityEvidence({ request, actorAliasLookup, preferredAliasNamespaces }) {
  const explicitEvidence = Array.isArray(request?.extensions?.peer_identity_evidence)
    ? request.extensions.peer_identity_evidence.map(normalizePeerIdentityEntry).filter(Boolean)
    : [];
  if (explicitEvidence.length > 0) {
    return explicitEvidence;
  }

  const actorRef = asNonEmptyString(request?.access_context_envelope?.actor_ref);
  if (!actorRef) {
    return [];
  }

  const actorAliases = actorAliasLookup.get(actorRef) ?? [];
  const pickedAlias = pickAliasForActor(actorAliases, preferredAliasNamespaces);
  return pickedAlias ? [pickedAlias] : [];
}

function buildRawIngressEvidence({ request, peerIdentityEvidence }) {
  return {
    request_id: request.request_id,
    trace_ref: request.trace_ref ?? null,
    channel_kind: request.channel_kind ?? 'wecom',
    message_mode: request.message_mode ?? 'direct_message',
    host_session_ref: request.extensions?.host_session_ref ?? request.session_ref ?? null,
    host_workspace_ref: request.extensions?.host_workspace_ref ?? null,
    host_conversation_ref: request.extensions?.host_conversation_ref ?? request.conversation_ref ?? null,
    peer_identity_evidence: peerIdentityEvidence,
    requested_capability_id: request.requested_capability_id,
    target_scope_hint: request.requested_scope_ref ?? request.access_context_envelope?.primary_scope_ref ?? null,
  };
}

export function createOwnerSideAuthKernelAdapter({
  aliasRegistryPath = defaultAliasRegistryPath,
  preferredAliasNamespaces = defaultPreferredAliasNamespaces,
  nowFactory = () => new Date().toISOString(),
} = {}) {
  const actorAliasLookup = loadActorAliasLookup(aliasRegistryPath);

  return {
    async evaluateCapabilityAccess(request) {
      if (!request || typeof request !== 'object') {
        throw new Error('owner-side auth adapter requires a capability access request object');
      }

      const peerIdentityEvidence = resolvePeerIdentityEvidence({
        request,
        actorAliasLookup,
        preferredAliasNamespaces,
      });
      if (peerIdentityEvidence.length === 0) {
        throw new Error('owner-side auth adapter cannot resolve peer_identity_evidence for capability access');
      }

      const result = runMilestoneBAccessChain({
        rawIngressEvidence: buildRawIngressEvidence({ request, peerIdentityEvidence }),
        requestedCapabilityId: request.requested_capability_id,
        requestedScopeRef: request.requested_scope_ref ?? null,
        now: nowFactory(),
      });

      return {
        access_decision: result.access_decision,
        access_context_envelope: result.access_context_envelope,
        extensions: {
          gate0_result: result.gate0_result,
          binding_snapshot_ref: result.binding_snapshot?.binding_snapshot_ref ?? null,
        },
      };
    },
  };
}
