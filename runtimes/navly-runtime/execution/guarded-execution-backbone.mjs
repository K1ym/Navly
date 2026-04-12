import {
  normalizeReasonCodes,
  todayIsoDate,
  validateAccessContextEnvelopeShape,
  validateAccessDecisionShape,
  validateReadinessResponseShape,
  validateThemeServiceResponseShape,
} from '../contracts/shared-contract-alignment.mjs';

function assertAdapterMethod(adapter, methodName, adapterName) {
  if (!adapter || typeof adapter[methodName] !== 'function') {
    throw new Error(`${adapterName}.${methodName} is required for runtime guarded execution`);
  }
}

function buildDependencyError(baseOutput, reasonCodes, errorMessage, extra = {}) {
  return {
    ...baseOutput,
    dependency_stage: 'dependency_error',
    reason_codes: normalizeReasonCodes(reasonCodes, 'runtime.dependency.unclassified'),
    error_message: errorMessage,
    ...extra,
  };
}

function pickString(value) {
  return typeof value === 'string' && value.trim().length > 0 ? value : null;
}

function buildAuthAdapterContext(interactionContext) {
  const slots = interactionContext.structured_input_slots ?? {};
  return {
    peer_identity_evidence: Array.isArray(slots.auth_peer_identity_evidence) ? slots.auth_peer_identity_evidence : null,
    host_session_ref: pickString(slots.host_session_ref),
    host_workspace_ref: pickString(slots.host_workspace_ref),
    host_conversation_ref: pickString(slots.host_conversation_ref),
  };
}

function buildDataAdapterContext(interactionContext) {
  const slots = interactionContext.structured_input_slots ?? {};
  return {
    org_id: pickString(slots.data_org_id),
    start_time: pickString(slots.data_window_start_time),
    end_time: pickString(slots.data_window_end_time),
    app_secret: pickString(slots.data_app_secret),
    fixture_bundle_path: pickString(slots.data_fixture_bundle_path),
    transport_kind: pickString(slots.data_transport_kind),
    live_base_url: pickString(slots.data_live_base_url),
    live_authorization: pickString(slots.data_live_authorization),
    live_token: pickString(slots.data_live_token),
    live_timeout_ms: pickString(slots.data_live_timeout_ms),
  };
}

function buildCapabilityAccessRequest({ interactionContext, executionPlan }) {
  return {
    request_id: interactionContext.request_id,
    trace_ref: interactionContext.trace_ref,
    channel_kind: interactionContext.channel_kind,
    message_mode: interactionContext.message_mode,
    session_ref: interactionContext.access_context_envelope.session_ref,
    conversation_ref: interactionContext.access_context_envelope.conversation_ref,
    prior_decision_ref: interactionContext.decision_ref,
    requested_capability_id: executionPlan.selected_capability_id,
    requested_scope_ref: executionPlan.target_scope_ref,
    requested_service_object_id: executionPlan.selected_service_object_id,
    access_context_envelope: interactionContext.access_context_envelope,
    operation_kind: 'read',
    runtime_trace_ref: interactionContext.runtime_trace_ref,
    extensions: buildAuthAdapterContext(interactionContext),
  };
}

function resolveEffectiveAccessContext({ interactionContext, capabilityAccessResponse }) {
  if (capabilityAccessResponse?.access_context_envelope) {
    return validateAccessContextEnvelopeShape(capabilityAccessResponse.access_context_envelope);
  }

  return interactionContext.access_context_envelope;
}

function buildReadinessQuery({ interactionContext, executionPlan, effectiveAccessContext, accessDecision }) {
  const dataAdapterContext = buildDataAdapterContext(interactionContext);

  return {
    request_id: interactionContext.request_id,
    trace_ref: interactionContext.trace_ref,
    capability_id: executionPlan.selected_capability_id,
    access_context: effectiveAccessContext,
    target_scope_ref: accessDecision.target_scope_ref ?? executionPlan.target_scope_ref,
    target_business_date: executionPlan.target_business_date,
    freshness_mode: executionPlan.freshness_mode,
    extensions: {
      runtime_trace_ref: interactionContext.runtime_trace_ref,
      selected_service_object_id: executionPlan.selected_service_object_id,
      data_adapter_context: dataAdapterContext,
    },
  };
}

function resolveServiceBusinessDate({ executionPlan, readinessResponse }) {
  if (executionPlan.freshness_mode === 'latest_usable' && readinessResponse.latest_usable_business_date) {
    return readinessResponse.latest_usable_business_date;
  }

  return executionPlan.target_business_date ?? todayIsoDate();
}

function buildThemeServiceQuery({
  interactionContext,
  executionPlan,
  effectiveAccessContext,
  accessDecision,
  readinessResponse,
}) {
  const dataAdapterContext = buildDataAdapterContext(interactionContext);

  return {
    request_id: interactionContext.request_id,
    trace_ref: interactionContext.trace_ref,
    capability_id: executionPlan.selected_capability_id,
    service_object_id: executionPlan.selected_service_object_id,
    access_context: effectiveAccessContext,
    target_scope_ref: accessDecision.target_scope_ref ?? readinessResponse.evaluated_scope_ref,
    target_business_date: resolveServiceBusinessDate({ executionPlan, readinessResponse }),
    include_explanation: executionPlan.include_explanation,
    extensions: {
      runtime_trace_ref: interactionContext.runtime_trace_ref,
      readiness_latest_usable_business_date: readinessResponse.latest_usable_business_date,
      data_adapter_context: dataAdapterContext,
    },
  };
}

export async function runGuardedExecution({
  interactionContext,
  executionPlan,
  authKernelClient,
  dataPlatformClient,
}) {
  assertAdapterMethod(authKernelClient, 'evaluateCapabilityAccess', 'authKernelClient');
  assertAdapterMethod(dataPlatformClient, 'queryCapabilityReadiness', 'dataPlatformClient');
  assertAdapterMethod(dataPlatformClient, 'queryThemeService', 'dataPlatformClient');

  const capabilityAccessRequest = buildCapabilityAccessRequest({ interactionContext, executionPlan });

  let capabilityAccessResponse;
  try {
    capabilityAccessResponse = await authKernelClient.evaluateCapabilityAccess(capabilityAccessRequest);
  } catch (error) {
    return {
      dependency_stage: 'dependency_error',
      reason_codes: ['runtime.dependency.auth_error'],
      error_message: error?.message ?? 'auth dependency call failed',
      capability_access_request: capabilityAccessRequest,
      capability_access_response: null,
      effective_access_context: interactionContext.access_context_envelope,
      readiness_query: null,
      readiness_response: null,
      theme_service_query: null,
      theme_service_response: null,
    };
  }

  if (!capabilityAccessResponse?.access_decision) {
    return {
      capability_access_request: capabilityAccessRequest,
      capability_access_response: capabilityAccessResponse ?? null,
      effective_access_context: interactionContext.access_context_envelope,
      readiness_query: null,
      readiness_response: null,
      theme_service_query: null,
      theme_service_response: null,
      dependency_stage: 'dependency_error',
      reason_codes: ['runtime.dependency.auth_missing_access_decision'],
      error_message: 'auth dependency did not return access_decision',
    };
  }

  const baseOutput = {
    capability_access_request: capabilityAccessRequest,
    capability_access_response: capabilityAccessResponse,
    effective_access_context: interactionContext.access_context_envelope,
    readiness_query: null,
    readiness_response: null,
    theme_service_query: null,
    theme_service_response: null,
    reason_codes: [],
    error_message: null,
  };

  let accessDecision;
  let effectiveAccessContext;
  try {
    accessDecision = validateAccessDecisionShape(capabilityAccessResponse.access_decision);
    effectiveAccessContext = resolveEffectiveAccessContext({
      interactionContext,
      capabilityAccessResponse,
    });
  } catch (error) {
    return buildDependencyError(
      baseOutput,
      ['runtime.dependency.auth_invalid_response'],
      error?.message ?? 'auth dependency returned invalid response',
    );
  }

  if (accessDecision.decision_status === 'deny') {
    return {
      ...baseOutput,
      effective_access_context: effectiveAccessContext,
      dependency_stage: 'access_denied',
      reason_codes: normalizeReasonCodes(accessDecision.reason_codes, 'runtime.access.denied'),
    };
  }

  if (accessDecision.decision_status === 'escalation') {
    return {
      ...baseOutput,
      effective_access_context: effectiveAccessContext,
      dependency_stage: 'access_escalated',
      reason_codes: normalizeReasonCodes(accessDecision.reason_codes, 'runtime.access.escalation'),
    };
  }

  const readinessQuery = buildReadinessQuery({
    interactionContext,
    executionPlan,
    effectiveAccessContext,
    accessDecision,
  });

  let readinessResponse;
  try {
    readinessResponse = await dataPlatformClient.queryCapabilityReadiness(readinessQuery);
  } catch (error) {
    return buildDependencyError(
      {
        ...baseOutput,
        effective_access_context: effectiveAccessContext,
        readiness_query: readinessQuery,
      },
      ['runtime.dependency.readiness_error'],
      error?.message ?? 'readiness dependency call failed',
    );
  }

  try {
    readinessResponse = validateReadinessResponseShape(readinessResponse);
  } catch (error) {
    return buildDependencyError(
      {
        ...baseOutput,
        effective_access_context: effectiveAccessContext,
        readiness_query: readinessQuery,
      },
      ['runtime.dependency.readiness_invalid_response'],
      error?.message ?? 'readiness dependency returned invalid response',
    );
  }

  if (readinessResponse.readiness_status !== 'ready') {
    return {
      ...baseOutput,
      effective_access_context: effectiveAccessContext,
      dependency_stage: 'readiness_blocked',
      reason_codes: normalizeReasonCodes(readinessResponse.reason_codes, `runtime.readiness.${readinessResponse.readiness_status}`),
      readiness_query: readinessQuery,
      readiness_response: readinessResponse,
    };
  }

  const themeServiceQuery = buildThemeServiceQuery({
    interactionContext,
    executionPlan,
    effectiveAccessContext,
    accessDecision,
    readinessResponse,
  });

  let themeServiceResponse;
  try {
    themeServiceResponse = await dataPlatformClient.queryThemeService(themeServiceQuery);
  } catch (error) {
    return buildDependencyError(
      {
        ...baseOutput,
        effective_access_context: effectiveAccessContext,
        readiness_query: readinessQuery,
        readiness_response: readinessResponse,
        theme_service_query: themeServiceQuery,
      },
      ['runtime.dependency.service_error'],
      error?.message ?? 'theme service dependency call failed',
    );
  }

  try {
    themeServiceResponse = validateThemeServiceResponseShape(themeServiceResponse);
  } catch (error) {
    return buildDependencyError(
      {
        ...baseOutput,
        effective_access_context: effectiveAccessContext,
        readiness_query: readinessQuery,
        readiness_response: readinessResponse,
        theme_service_query: themeServiceQuery,
      },
      ['runtime.dependency.service_invalid_response'],
      error?.message ?? 'theme service dependency returned invalid response',
    );
  }

  if (themeServiceResponse.service_status !== 'served') {
    return {
      ...baseOutput,
      effective_access_context: effectiveAccessContext,
      dependency_stage: 'service_not_served',
      reason_codes: normalizeReasonCodes(
        themeServiceResponse.explanation_object?.reason_codes,
        `runtime.service.${themeServiceResponse.service_status}`,
      ),
      readiness_query: readinessQuery,
      readiness_response: readinessResponse,
      theme_service_query: themeServiceQuery,
      theme_service_response: themeServiceResponse,
    };
  }

  return {
    ...baseOutput,
    effective_access_context: effectiveAccessContext,
    dependency_stage: 'served',
    reason_codes: [],
    readiness_query: readinessQuery,
    readiness_response: readinessResponse,
    theme_service_query: themeServiceQuery,
    theme_service_response: themeServiceResponse,
  };
}
