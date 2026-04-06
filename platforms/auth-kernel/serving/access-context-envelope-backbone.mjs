import { loadPolicyCatalog } from '../policy-catalog/policy-catalog-loader.mjs';
import { validateAccessContextEnvelopeShape } from '../contracts/shared-contract-alignment.mjs';

function expiresAt(now, minutes = 30) {
  return new Date(Date.parse(now) + minutes * 60 * 1000).toISOString();
}

function collectGrantedCapabilities(roleIds, policyCatalog) {
  const capabilityIds = new Set();
  for (const roleId of roleIds) {
    for (const capabilityId of policyCatalog.grantProfileByRoleId.get(roleId) ?? []) {
      capabilityIds.add(capabilityId);
    }
  }
  return [...capabilityIds];
}

export function buildAccessContextEnvelope({
  requestId,
  traceRef,
  accessDecision,
  bindingSnapshot,
  now = new Date().toISOString(),
  policyCatalog = loadPolicyCatalog(),
}) {
  if (!accessDecision?.decision_ref) {
    return null;
  }

  if (!['allow', 'restricted'].includes(accessDecision.decision_status)) {
    return null;
  }

  if (!bindingSnapshot.selected_scope_ref) {
    return null;
  }

  const accessContextEnvelope = {
    request_id: requestId,
    trace_ref: traceRef,
    decision_ref: accessDecision.decision_ref,
    actor_ref: bindingSnapshot.actor_ref,
    session_ref: bindingSnapshot.session_ref,
    conversation_ref: bindingSnapshot.conversation_ref,
    tenant_ref: bindingSnapshot.tenant_ref,
    primary_scope_ref: bindingSnapshot.selected_scope_ref,
    granted_scope_refs: bindingSnapshot.granted_scope_refs,
    granted_capability_ids: collectGrantedCapabilities(bindingSnapshot.role_ids, policyCatalog),
    issued_at: now,
    expires_at: expiresAt(now),
    extensions: {
      binding_snapshot_ref: bindingSnapshot.binding_snapshot_ref,
      conversation_binding_status: bindingSnapshot.conversation_binding_status,
    },
  };

  validateAccessContextEnvelopeShape(accessContextEnvelope);
  return accessContextEnvelope;
}
