import { assertCapabilityId, assertMatchesSharedPattern, buildTraceRef, sharedPatterns } from '../contracts/shared-contract-alignment.mjs';

export function normalizeHostEvidence(rawEvidence) {
  if (!rawEvidence || typeof rawEvidence !== 'object') {
    throw new Error('host evidence must be an object');
  }

  if (!rawEvidence.request_id) {
    throw new Error('host evidence must include request_id');
  }

  const traceRef = rawEvidence.trace_ref ?
    assertMatchesSharedPattern('trace_ref', rawEvidence.trace_ref, sharedPatterns.traceRef) :
    buildTraceRef(rawEvidence.request_id);

  if (!Array.isArray(rawEvidence.peer_identity_evidence) || rawEvidence.peer_identity_evidence.length === 0) {
    throw new Error('host evidence must include peer_identity_evidence');
  }

  const peerIdentityEvidence = rawEvidence.peer_identity_evidence.map((entry) => {
    if (!entry.alias_namespace || !entry.alias_value) {
      throw new Error('peer identity evidence entries must include alias_namespace and alias_value');
    }
    return {
      alias_namespace: String(entry.alias_namespace),
      alias_value: String(entry.alias_value),
    };
  });

  if (rawEvidence.requested_capability_id) {
    assertCapabilityId(rawEvidence.requested_capability_id);
  }

  return {
    request_id: String(rawEvidence.request_id),
    trace_ref: traceRef,
    channel_kind: String(rawEvidence.channel_kind ?? 'wecom'),
    message_mode: String(rawEvidence.message_mode ?? 'direct_message'),
    host_session_ref: rawEvidence.host_session_ref ? String(rawEvidence.host_session_ref) : null,
    host_workspace_ref: rawEvidence.host_workspace_ref ? String(rawEvidence.host_workspace_ref) : null,
    host_conversation_ref: rawEvidence.host_conversation_ref ? String(rawEvidence.host_conversation_ref) : null,
    peer_identity_evidence: peerIdentityEvidence,
    requested_capability_id: rawEvidence.requested_capability_id ?? null,
    target_scope_hint: rawEvidence.target_scope_hint ?? null,
  };
}
