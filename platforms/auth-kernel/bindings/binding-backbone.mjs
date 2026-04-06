import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import {
  assertMatchesSharedPattern,
  buildConversationRef,
  buildDeterministicId,
  buildSessionRef,
  sharedPatterns,
} from '../contracts/shared-contract-alignment.mjs';

const moduleDir = path.dirname(fileURLToPath(import.meta.url));

function readJsonSeed(fileName) {
  return JSON.parse(fs.readFileSync(path.join(moduleDir, fileName), 'utf8'));
}

function deriveConversationRef(ingressEvidence) {
  const rawConversationKey = ingressEvidence.host_conversation_ref || ingressEvidence.host_session_ref || ingressEvidence.request_id;
  return buildConversationRef(buildDeterministicId('conversation', ingressEvidence.channel_kind, rawConversationKey));
}

function deriveSessionRef(actorRef, conversationRef) {
  return buildSessionRef(buildDeterministicId('session', actorRef, conversationRef));
}

export function computeBindingSnapshotRef(bindingSnapshot) {
  return `navly:binding-snapshot:${buildDeterministicId(
    'binding',
    bindingSnapshot.actor_ref ?? 'none',
    bindingSnapshot.tenant_ref ?? 'none',
    bindingSnapshot.conversation_ref ?? 'none',
    [...(bindingSnapshot.role_ids ?? [])].sort().join(','),
    [...(bindingSnapshot.granted_scope_refs ?? [])].sort().join(','),
    bindingSnapshot.primary_scope_ref ?? 'none',
    bindingSnapshot.selected_scope_ref ?? 'none',
    bindingSnapshot.conversation_binding_status ?? 'none',
    [...(bindingSnapshot.reason_codes ?? [])].sort().join(','),
  )}`;
}

export function loadBindingBackbone() {
  return {
    roleBindings: readJsonSeed('role-binding.seed.json').bindings ?? [],
    scopeBindings: readJsonSeed('scope-binding.seed.json').bindings ?? [],
    conversationBindingProfile: readJsonSeed('conversation-binding.seed.json'),
  };
}

export function buildBindingSnapshot({
  ingressEvidence,
  actorResolutionResult,
  bindingBackbone = loadBindingBackbone(),
  selectedScopeHint = ingressEvidence.target_scope_hint ?? null,
  now = new Date().toISOString(),
}) {
  const conversationRef = deriveConversationRef(ingressEvidence);

  if (actorResolutionResult.resolution_status !== 'resolved') {
    const unresolvedSnapshot = {
      actor_ref: actorResolutionResult.actor_ref ?? null,
      tenant_ref: actorResolutionResult.tenant_ref ?? null,
      role_ids: [],
      granted_scope_refs: [],
      primary_scope_ref: null,
      selected_scope_ref: null,
      conversation_ref: conversationRef,
      session_ref: null,
      conversation_binding_status: 'suspended',
      reason_codes: [...(actorResolutionResult.reason_codes ?? [])],
      generated_at: now,
    };

    return {
      ...unresolvedSnapshot,
      binding_snapshot_ref: computeBindingSnapshotRef(unresolvedSnapshot),
    };
  }

  const actorRef = actorResolutionResult.actor_ref;
  const tenantRef = actorResolutionResult.tenant_ref;
  const roleIds = bindingBackbone.roleBindings
    .filter((binding) => binding.actor_ref === actorRef)
    .map((binding) => binding.role_id);

  const actorScopeBindings = bindingBackbone.scopeBindings.filter((binding) => binding.actor_ref === actorRef);
  const tenantScopedBindings = actorScopeBindings.filter((binding) => binding.tenant_ref === tenantRef);
  const hasTenantMismatch = tenantScopedBindings.length !== actorScopeBindings.length;

  let grantedScopeRefs = tenantScopedBindings.map((binding) => {
    assertMatchesSharedPattern('scope_ref', binding.scope_ref, sharedPatterns.scopeRef);
    return binding.scope_ref;
  });
  let primaryScopeRef = tenantScopedBindings.find((binding) => binding.is_primary)?.scope_ref ?? grantedScopeRefs[0] ?? null;

  let conversationBindingStatus = 'bound';
  let selectedScopeRef = null;
  const reasonCodes = [];

  if (hasTenantMismatch) {
    grantedScopeRefs = [];
    primaryScopeRef = null;
    conversationBindingStatus = 'suspended';
    reasonCodes.push('tenant_mismatch');
  } else if (selectedScopeHint) {
    if (grantedScopeRefs.includes(selectedScopeHint)) {
      selectedScopeRef = selectedScopeHint;
    } else {
      conversationBindingStatus = bindingBackbone.conversationBindingProfile.invalid_scope_selection_status;
      reasonCodes.push('invalid_scope_selection');
    }
  } else if (grantedScopeRefs.length === 1 && bindingBackbone.conversationBindingProfile.auto_bind_single_scope) {
    selectedScopeRef = grantedScopeRefs[0];
  } else if (grantedScopeRefs.length > 1) {
    conversationBindingStatus = bindingBackbone.conversationBindingProfile.multi_scope_without_selection_status;
    reasonCodes.push('scope_unbound');
  } else {
    conversationBindingStatus = 'suspended';
    reasonCodes.push('binding_missing');
  }

  const bindingSnapshot = {
    actor_ref: actorRef,
    tenant_ref: tenantRef,
    role_ids: roleIds,
    granted_scope_refs: grantedScopeRefs,
    primary_scope_ref: conversationBindingStatus === 'bound' ? (selectedScopeRef ?? primaryScopeRef) : null,
    selected_scope_ref: selectedScopeRef,
    conversation_ref: conversationRef,
    session_ref: deriveSessionRef(actorRef, conversationRef),
    conversation_binding_status: conversationBindingStatus,
    reason_codes: reasonCodes,
    generated_at: now,
  };

  return {
    ...bindingSnapshot,
    binding_snapshot_ref: computeBindingSnapshotRef(bindingSnapshot),
  };
}

export function applyScopeSelectionToBindingSnapshot({ bindingSnapshot, requestedScopeRef, now = new Date().toISOString() }) {
  if (!requestedScopeRef) {
    return bindingSnapshot;
  }

  assertMatchesSharedPattern('requested_scope_ref', requestedScopeRef, sharedPatterns.scopeRef);

  const nextSnapshot = !bindingSnapshot.granted_scope_refs.includes(requestedScopeRef)
    ? {
        ...bindingSnapshot,
        selected_scope_ref: null,
        primary_scope_ref: null,
        conversation_binding_status: 'suspended',
        reason_codes: ['invalid_scope_selection'],
        generated_at: now,
      }
    : {
        ...bindingSnapshot,
        selected_scope_ref: requestedScopeRef,
        primary_scope_ref: requestedScopeRef,
        conversation_binding_status: 'bound',
        reason_codes: [],
        generated_at: now,
      };

  return {
    ...nextSnapshot,
    binding_snapshot_ref: computeBindingSnapshotRef(nextSnapshot),
  };
}
