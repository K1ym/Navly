import { runMilestoneBAccessChain } from '../../../../platforms/auth-kernel/serving/access-chain-backbone.mjs';
import { runMilestoneBGuardedExecutionChain } from '../../../../runtimes/navly-runtime/execution/runtime-chain-backbone.mjs';
import { enforceGate0Result } from '../../auth-linkage/gate0-enforcement-backbone.mjs';
import { assembleIngressIdentityEnvelope } from '../../auth-linkage/ingress-identity-envelope-backbone.mjs';
import { buildAuthorizedSessionLink } from '../../auth-linkage/authorized-session-link-backbone.mjs';
import { createMilestoneBTraceBundle } from '../../diagnostics/host-trace-backbone.mjs';
import { buildHostDispatchResult } from '../../dispatch/host-dispatch-handoff-backbone.mjs';
import { normalizeOpenClawHostIngress } from '../../ingress/host-ingress-normalizer.mjs';
import { buildRuntimeRequestEnvelope } from '../../runtime-handoff/runtime-request-envelope-backbone.mjs';
import {
  buildFirstPartyToolPublicationManifest,
  findPublishedTool,
} from '../../tool-publication/first-party-host-surface.mjs';
import {
  ensureObject,
  normalizeOptionalString,
  sharedPatterns,
  validateAccessContextEnvelopeShape,
} from './bridge-shared-alignment.mjs';

function assertRequiredString(label, value) {
  const normalized = normalizeOptionalString(value);
  if (!normalized) {
    throw new Error(`${label} is required`);
  }
  return normalized;
}

function validateToolInputValue(fieldName, value) {
  if (value === undefined || value === null) {
    return value;
  }

  if (fieldName === 'scope_ref') {
    if (typeof value !== 'string' || !sharedPatterns.scopeRef.test(value)) {
      throw new Error(`tool input scope_ref must match scope_ref pattern, received ${value}`);
    }
    return value;
  }

  if (fieldName === 'business_date' || fieldName === 'backfill_from' || fieldName === 'backfill_to') {
    if (typeof value !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(value)) {
      throw new Error(`tool input ${fieldName} must use YYYY-MM-DD format`);
    }
    return value;
  }

  if (fieldName === 'include_explanation') {
    if (typeof value !== 'boolean') {
      throw new Error('tool input include_explanation must be boolean');
    }
    return value;
  }

  if (fieldName === 'time_window') {
    if (!value || typeof value !== 'object' || Array.isArray(value)) {
      throw new Error('tool input time_window must be an object');
    }
    return value;
  }

  return value;
}

function normalizeToolInput(tool, toolInput = {}) {
  const normalizedInput = ensureObject('toolInput', toolInput);
  const allowedInputFields = new Set(tool.allowed_input_fields ?? []);

  const unknownFields = Object.keys(normalizedInput).filter((fieldName) => !allowedInputFields.has(fieldName));
  if (unknownFields.length > 0) {
    throw new Error(`tool ${tool.tool_name} received unsupported input fields: ${unknownFields.join(', ')}`);
  }

  const output = {};
  for (const [fieldName, value] of Object.entries(normalizedInput)) {
    output[fieldName] = validateToolInputValue(fieldName, value);
  }
  return output;
}

function normalizeHostAgentSelection(selection, defaultAgentId) {
  if (!selection) {
    return {
      agent_id: defaultAgentId,
      carrier_mode: 'host_isolation_only',
      carrier_ref: null,
    };
  }

  return {
    agent_id: assertRequiredString('hostAgentSelection.agent_id', selection.agent_id),
    carrier_mode: normalizeOptionalString(selection.carrier_mode) ?? 'host_isolation_only',
    carrier_ref: normalizeOptionalString(selection.carrier_ref),
  };
}

function buildStructuredInputSlots({
  rawHostIngress,
  normalizedToolInput,
  runtimeDataContext,
  publishedTool,
}) {
  const baseSlots = rawHostIngress.structured_input_slots && typeof rawHostIngress.structured_input_slots === 'object'
    ? { ...rawHostIngress.structured_input_slots }
    : {};
  const timeWindow = normalizedToolInput.time_window && typeof normalizedToolInput.time_window === 'object'
    ? normalizedToolInput.time_window
    : null;

  return {
    ...baseSlots,
    host_session_ref: normalizeOptionalString(rawHostIngress.host_session_ref),
    host_workspace_ref: normalizeOptionalString(rawHostIngress.host_workspace_ref),
    host_conversation_ref: normalizeOptionalString(rawHostIngress.host_conversation_ref),
    auth_peer_identity_evidence: Array.isArray(rawHostIngress.peer_identity_evidence)
      ? rawHostIngress.peer_identity_evidence
      : undefined,
    freshness_mode: normalizeOptionalString(normalizedToolInput.freshness_mode) ?? baseSlots.freshness_mode,
    include_explanation: normalizedToolInput.include_explanation ?? true,
    comparison_mode: normalizeOptionalString(normalizedToolInput.comparison_mode),
    rerun_mode: normalizeOptionalString(normalizedToolInput.rerun_mode),
    backfill_from: normalizeOptionalString(normalizedToolInput.backfill_from),
    backfill_to: normalizeOptionalString(normalizedToolInput.backfill_to),
    target_business_date: normalizeOptionalString(normalizedToolInput.business_date),
    data_window_start_time: normalizeOptionalString(
      timeWindow?.start_time ?? timeWindow?.start ?? timeWindow?.from ?? runtimeDataContext.data_window_start_time,
    ),
    data_window_end_time: normalizeOptionalString(
      timeWindow?.end_time ?? timeWindow?.end ?? timeWindow?.to ?? runtimeDataContext.data_window_end_time,
    ),
    data_transport_kind: normalizeOptionalString(runtimeDataContext.data_transport_kind),
    data_live_base_url: normalizeOptionalString(runtimeDataContext.data_live_base_url),
    data_live_authorization: normalizeOptionalString(runtimeDataContext.data_live_authorization),
    data_live_token: normalizeOptionalString(runtimeDataContext.data_live_token),
    data_live_timeout_ms: normalizeOptionalString(runtimeDataContext.data_live_timeout_ms),
    data_org_id: normalizeOptionalString(runtimeDataContext.data_org_id),
    data_app_secret: normalizeOptionalString(runtimeDataContext.data_app_secret),
    data_fixture_bundle_path: normalizeOptionalString(runtimeDataContext.data_fixture_bundle_path),
    host_tool_name: publishedTool.tool_name,
    host_skill_ids: publishedTool.skill_ids,
  };
}

export function buildToolAwareRawHostIngress({
  rawHostIngress,
  publishedTool,
  toolInput = {},
  runtimeDataContext = {},
}) {
  const baseIngress = ensureObject('rawHostIngress', rawHostIngress);
  const normalizedToolInput = normalizeToolInput(publishedTool, toolInput);

  return {
    ...baseIngress,
    message_text: normalizeOptionalString(baseIngress.message_text) ?? `Host tool invocation ${publishedTool.tool_name}`,
    requested_capability_id: publishedTool.capability_id,
    requested_service_object_id: publishedTool.service_object_id,
    target_scope_hint: normalizeOptionalString(normalizedToolInput.scope_ref) ?? normalizeOptionalString(baseIngress.target_scope_hint),
    target_business_date_hint: normalizeOptionalString(normalizedToolInput.business_date)
      ?? normalizeOptionalString(baseIngress.target_business_date_hint),
    structured_input_slots: buildStructuredInputSlots({
      rawHostIngress: baseIngress,
      normalizedToolInput,
      runtimeDataContext,
      publishedTool,
    }),
  };
}

function validateRequiredInvocationContext({ rawHostIngress, decisionRef, accessContextEnvelope }) {
  assertRequiredString('rawHostIngress.request_id', rawHostIngress.request_id);
  assertRequiredString('rawHostIngress.trace_ref', rawHostIngress.trace_ref);

  if (accessContextEnvelope) {
    validateAccessContextEnvelopeShape(accessContextEnvelope);
  }

  if (decisionRef && accessContextEnvelope && accessContextEnvelope.decision_ref !== decisionRef) {
    throw new Error('decisionRef must match access_context_envelope.decision_ref');
  }
}

export async function runFirstPartyLiveHostTool({
  toolName,
  rawHostIngress,
  toolInput = {},
  gate0Result = null,
  accessContextEnvelope = null,
  decisionRef = null,
  hostAgentSelection = null,
  runtimeDataContext = {},
  publicationManifest = buildFirstPartyToolPublicationManifest(),
  accessChainExecutor = runMilestoneBAccessChain,
  runtimeExecutor = runMilestoneBGuardedExecutionChain,
  runtimeExecutorOptions = {},
  now = new Date().toISOString(),
}) {
  const publishedTool = findPublishedTool({ toolName, manifest: publicationManifest });
  if (!publishedTool) {
    throw new Error(`unknown first-party host tool ${toolName}`);
  }

  const normalizedToolInput = normalizeToolInput(publishedTool, toolInput);
  const toolAwareRawHostIngress = buildToolAwareRawHostIngress({
    rawHostIngress,
    publishedTool,
    toolInput: normalizedToolInput,
    runtimeDataContext,
  });

  let liveAccessChain = null;
  let resolvedGate0Result = gate0Result;
  let resolvedAccessContextEnvelope = accessContextEnvelope;
  let resolvedDecisionRef = decisionRef;

  if (!resolvedGate0Result) {
    liveAccessChain = accessChainExecutor({
      rawIngressEvidence: toolAwareRawHostIngress,
      requestedCapabilityId: publishedTool.capability_id,
      requestedScopeRef: normalizedToolInput.scope_ref ?? null,
      now,
    });
    resolvedGate0Result = liveAccessChain.gate0_result;
    resolvedAccessContextEnvelope = liveAccessChain.access_context_envelope;
    resolvedDecisionRef = resolvedAccessContextEnvelope?.decision_ref
      ?? liveAccessChain.access_decision?.decision_ref
      ?? liveAccessChain.gate0_result?.decision_ref
      ?? null;
  }

  validateRequiredInvocationContext({
    rawHostIngress: toolAwareRawHostIngress,
    decisionRef: resolvedDecisionRef,
    accessContextEnvelope: resolvedAccessContextEnvelope,
  });

  const hostIngressEnvelope = normalizeOpenClawHostIngress({
    rawHostIngress: toolAwareRawHostIngress,
    now,
  });
  const ingressIdentityEnvelope = assembleIngressIdentityEnvelope({ hostIngressEnvelope });
  const gate0Enforcement = enforceGate0Result({
    hostIngressEnvelope,
    gate0Result: resolvedGate0Result,
    accessContextEnvelope: resolvedAccessContextEnvelope,
    now,
  });
  const authorizedSessionLink = buildAuthorizedSessionLink({
    hostIngressEnvelope,
    gate0Enforcement,
    accessContextEnvelope: resolvedAccessContextEnvelope,
    now,
  });
  const runtimeRequestEnvelope = buildRuntimeRequestEnvelope({
    hostIngressEnvelope,
    gate0Enforcement,
    authorizedSessionLink,
    accessContextEnvelope: resolvedAccessContextEnvelope,
  });

  let runtimePipeline = null;
  let runtimeResultEnvelope = null;
  if (runtimeRequestEnvelope) {
    runtimePipeline = await runtimeExecutor({
      runtimeRequestEnvelope,
      now,
      ...runtimeExecutorOptions,
    });
    runtimeResultEnvelope = runtimePipeline.runtime_result_envelope;
  }

  const hostDispatchResult = buildHostDispatchResult({
    hostIngressEnvelope,
    gate0Enforcement,
    authorizedSessionLink,
    runtimeRequestEnvelope,
    runtimeResultEnvelope,
    now,
  });
  const hostTraceEvents = createMilestoneBTraceBundle({
    hostIngressEnvelope,
    ingressIdentityEnvelope,
    gate0Enforcement,
    authorizedSessionLink,
    runtimeRequestEnvelope,
    hostDispatchResult,
    runtimeResultEnvelope,
    now,
  });

  return {
    publication_manifest: publicationManifest,
    published_tool: publishedTool,
    host_agent_selection: normalizeHostAgentSelection(hostAgentSelection, publishedTool.host_agent_id),
    tool_input: normalizedToolInput,
    tool_aware_raw_host_ingress: toolAwareRawHostIngress,
    live_access_chain: liveAccessChain,
    host_ingress_envelope: hostIngressEnvelope,
    ingress_identity_envelope: ingressIdentityEnvelope,
    gate0_enforcement: gate0Enforcement,
    authorized_session_link: authorizedSessionLink,
    runtime_request_envelope: runtimeRequestEnvelope,
    runtime_pipeline: runtimePipeline,
    host_dispatch_result: hostDispatchResult,
    host_trace_events: hostTraceEvents,
  };
}
