import {
  asArray,
  assertCapabilityId,
  assertServiceObjectId,
  buildDeterministicId,
  buildHostLocalRef,
  buildIngressRef,
  buildTraceRef,
  ensureObject,
  normalizeOptionalString,
} from '../adapters/openclaw/bridge-shared-alignment.mjs';

function deriveDefaultDispatchMode(messageMode) {
  switch (messageMode) {
    case 'thread_message':
      return 'thread_reply';
    case 'group_message':
      return 'group_reply';
    default:
      return 'direct_reply';
  }
}

function normalizePeerIdentityEntry(entry, channelKind) {
  if (typeof entry === 'string') {
    return {
      alias_namespace: `${channelKind}_user_id`,
      alias_value: entry,
      evidence_source: 'host',
    };
  }

  if (!entry || typeof entry !== 'object') {
    throw new Error('peer identity evidence entries must be string or object');
  }

  const aliasNamespace = normalizeOptionalString(entry.alias_namespace) ?? `${channelKind}_user_id`;
  const aliasValue = normalizeOptionalString(entry.alias_value) ?? normalizeOptionalString(entry.peer_ref);

  if (!aliasValue) {
    throw new Error('peer identity evidence entries must include alias_value or peer_ref');
  }

  return {
    alias_namespace: aliasNamespace,
    alias_value: aliasValue,
    evidence_source: normalizeOptionalString(entry.evidence_source) ?? 'host',
  };
}

function normalizePeerIdentityEvidence(rawHostIngress, channelKind) {
  const entries = asArray(rawHostIngress.peer_identity_evidence ?? rawHostIngress.peer_identity_hint ?? []);
  if (!entries.length && normalizeOptionalString(rawHostIngress.wecom_user_id)) {
    entries.push({ alias_namespace: 'wecom_user_id', alias_value: rawHostIngress.wecom_user_id });
  }
  if (!entries.length) {
    throw new Error('rawHostIngress must include peer_identity_evidence');
  }
  return entries.map((entry) => normalizePeerIdentityEntry(entry, channelKind));
}

function buildDefaultResponseCapabilities(messageMode) {
  return {
    supports_text_reply: true,
    supports_thread_reply: messageMode === 'thread_message' || messageMode === 'group_message',
    supports_private_reply: messageMode !== 'group_message',
  };
}

function buildDefaultDeliveryContext({ messageMode, hostConversationRef, hostSessionRef }) {
  return {
    dispatch_mode: deriveDefaultDispatchMode(messageMode),
    target_ref: hostConversationRef ?? hostSessionRef,
  };
}

function normalizeTargetBusinessDateHint(value) {
  const normalized = normalizeOptionalString(value);
  if (!normalized) {
    return null;
  }
  if (!/^\d{4}-\d{2}-\d{2}$/.test(normalized)) {
    throw new Error(`target_business_date_hint must use YYYY-MM-DD format, received ${normalized}`);
  }
  return normalized;
}

export function normalizeOpenClawHostIngress({ rawHostIngress, now = new Date().toISOString() }) {
  const input = ensureObject('rawHostIngress', rawHostIngress);
  const channelKind = normalizeOptionalString(input.channel_kind) ?? 'wecom';
  const messageMode = normalizeOptionalString(input.message_mode) ?? 'direct_message';

  const requestId = normalizeOptionalString(input.request_id)
    ?? buildDeterministicId(
      'request',
      channelKind,
      input.host_session_ref ?? '',
      input.host_conversation_ref ?? '',
      input.host_message_ref ?? '',
      input.message_text ?? '',
      input.received_at ?? now,
    );

  const traceRef = input.trace_ref ? buildTraceRef(input.trace_ref.replace(/^navly:trace:/, '')) : buildTraceRef(requestId);
  const hostSessionRef = normalizeOptionalString(input.host_session_ref)
    ?? buildHostLocalRef('host-session', channelKind, input.host_conversation_ref ?? requestId);
  const hostConversationRef = normalizeOptionalString(input.host_conversation_ref)
    ?? buildHostLocalRef('host-conversation', channelKind, hostSessionRef);
  const hostWorkspaceRef = normalizeOptionalString(input.host_workspace_ref)
    ?? buildHostLocalRef('host-workspace', channelKind, 'default');
  const hostMessageRef = normalizeOptionalString(input.host_message_ref)
    ?? buildHostLocalRef('host-message', requestId, input.message_text ?? 'empty');
  const channelAccountRef = normalizeOptionalString(input.channel_account_ref)
    ?? buildHostLocalRef('channel-account', channelKind, hostWorkspaceRef);
  const ingressRef = normalizeOptionalString(input.ingress_ref)
    ?? buildIngressRef(channelKind, hostConversationRef, hostMessageRef, requestId);
  const hostTraceRef = normalizeOptionalString(input.host_trace_ref)
    ?? buildHostLocalRef('host-trace', requestId, hostConversationRef, hostMessageRef);

  const requestedCapabilityId = normalizeOptionalString(input.requested_capability_id);
  if (requestedCapabilityId) {
    assertCapabilityId(requestedCapabilityId);
  }

  const requestedServiceObjectId = normalizeOptionalString(input.requested_service_object_id);
  if (requestedServiceObjectId) {
    assertServiceObjectId(requestedServiceObjectId);
  }

  const responseChannelCapabilities = input.response_channel_capabilities && typeof input.response_channel_capabilities === 'object'
    ? input.response_channel_capabilities
    : buildDefaultResponseCapabilities(messageMode);

  const hostDeliveryContext = input.host_delivery_context && typeof input.host_delivery_context === 'object'
    ? input.host_delivery_context
    : buildDefaultDeliveryContext({
        messageMode,
        hostConversationRef,
        hostSessionRef,
      });

  return {
    object_name: 'host_ingress_envelope',
    object_scope: 'bridge_local',
    request_id: requestId,
    ingress_ref: ingressRef,
    trace_ref: traceRef,
    host_trace_ref: hostTraceRef,
    host_event_kind: normalizeOptionalString(input.host_event_kind) ?? 'chat_message',
    channel_kind: channelKind,
    message_mode: messageMode,
    channel_account_ref: channelAccountRef,
    host_session_ref: hostSessionRef,
    host_workspace_ref: hostWorkspaceRef,
    host_conversation_ref: hostConversationRef,
    host_message_ref: hostMessageRef,
    peer_identity_evidence: normalizePeerIdentityEvidence(input, channelKind),
    message_text: normalizeOptionalString(input.message_text) ?? '',
    attachment_refs: Array.isArray(input.attachment_refs) ? input.attachment_refs : [],
    structured_input_slots: input.structured_input_slots && typeof input.structured_input_slots === 'object'
      ? input.structured_input_slots
      : {},
    requested_capability_id: requestedCapabilityId,
    requested_service_object_id: requestedServiceObjectId,
    target_scope_hint: normalizeOptionalString(input.target_scope_hint),
    target_business_date_hint: normalizeTargetBusinessDateHint(input.target_business_date_hint),
    response_channel_capabilities: responseChannelCapabilities,
    host_delivery_context: hostDeliveryContext,
    received_at: normalizeOptionalString(input.received_at) ?? now,
  };
}
