import {
  normalizeReasonCodes,
  todayIsoDate,
  validateAccessContextEnvelopeShape,
  validateAccessDecisionShape,
  validateReadinessResponseShape,
  validateThemeServiceResponseShape,
} from '../contracts/shared-contract-alignment.mjs';

const EXPLANATION_SERVICE_OBJECT_ID = 'navly.service.system.capability_explanation';

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
    fixture_bundle_paths: Array.isArray(slots.data_fixture_bundle_paths)
      ? slots.data_fixture_bundle_paths.filter((value) => typeof value === 'string' && value.trim().length > 0)
      : null,
    transport_kind: pickString(slots.data_transport_kind),
    live_base_url: pickString(slots.data_live_base_url),
    live_authorization: pickString(slots.data_live_authorization),
    live_token: pickString(slots.data_live_token),
    live_timeout_ms: slots.data_live_timeout_ms ?? null,
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

function buildExplanationServiceQuery({
  interactionContext,
  executionPlan,
  effectiveAccessContext,
  accessDecision,
  readinessResponse,
}) {
  const baseQuery = buildThemeServiceQuery({
    interactionContext,
    executionPlan: {
      ...executionPlan,
      selected_service_object_id: EXPLANATION_SERVICE_OBJECT_ID,
    },
    effectiveAccessContext,
    accessDecision,
    readinessResponse,
  });

  return {
    ...baseQuery,
    extensions: {
      ...(baseQuery.extensions ?? {}),
      selected_service_object_id: EXPLANATION_SERVICE_OBJECT_ID,
    },
  };
}

function uniqueCodes(codes) {
  return [...new Set((codes ?? []).filter((code) => typeof code === 'string' && code.trim().length > 0))];
}

async function queryValidatedThemeService({
  dataPlatformClient,
  query,
  baseOutput,
  effectiveAccessContext,
  readinessQuery,
  readinessResponse,
}) {
  let themeServiceResponse;
  try {
    themeServiceResponse = await dataPlatformClient.queryThemeService(query);
  } catch (error) {
    return {
      ok: false,
      failure: buildDependencyError(
        {
          ...baseOutput,
          effective_access_context: effectiveAccessContext,
          readiness_query: readinessQuery,
          readiness_response: readinessResponse,
          theme_service_query: query,
        },
        ['runtime.dependency.service_error'],
        error?.message ?? 'theme service dependency call failed',
      ),
    };
  }

  try {
    themeServiceResponse = validateThemeServiceResponseShape(themeServiceResponse);
  } catch (error) {
    return {
      ok: false,
      failure: buildDependencyError(
        {
          ...baseOutput,
          effective_access_context: effectiveAccessContext,
          readiness_query: readinessQuery,
          readiness_response: readinessResponse,
          theme_service_query: query,
        },
        ['runtime.dependency.service_invalid_response'],
        error?.message ?? 'theme service dependency returned invalid response',
      ),
    };
  }

  return {
    ok: true,
    response: themeServiceResponse,
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
    explanation_service_query: null,
    explanation_service_response: null,
    reason_codes: [],
    error_message: null,
    access_decision_status: null,
    restriction_codes: [],
    obligation_codes: [],
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
      access_decision_status: accessDecision.decision_status,
      restriction_codes: uniqueCodes(accessDecision.restriction_codes),
      obligation_codes: uniqueCodes(accessDecision.obligation_codes),
    };
  }

  if (accessDecision.decision_status === 'escalation') {
    return {
      ...baseOutput,
      effective_access_context: effectiveAccessContext,
      dependency_stage: 'access_escalated',
      reason_codes: normalizeReasonCodes(accessDecision.reason_codes, 'runtime.access.escalation'),
      access_decision_status: accessDecision.decision_status,
      restriction_codes: uniqueCodes(accessDecision.restriction_codes),
      obligation_codes: uniqueCodes(accessDecision.obligation_codes),
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
    const readinessBlockedOutput = {
      ...baseOutput,
      effective_access_context: effectiveAccessContext,
      reason_codes: normalizeReasonCodes(
        accessDecision.reason_codes,
        accessDecision.decision_status === 'restricted' ? 'runtime.access.restricted' : null,
      ),
      readiness_query: readinessQuery,
      readiness_response: readinessResponse,
      access_decision_status: accessDecision.decision_status,
      restriction_codes: uniqueCodes(accessDecision.restriction_codes),
      obligation_codes: uniqueCodes(accessDecision.obligation_codes),
    };
    const explanationServiceQuery = buildExplanationServiceQuery({
      interactionContext,
      executionPlan,
      effectiveAccessContext,
      accessDecision,
      readinessResponse,
    });

    if (executionPlan.selected_service_object_id === EXPLANATION_SERVICE_OBJECT_ID) {
      const explanationServiceResult = await queryValidatedThemeService({
        dataPlatformClient,
        query: explanationServiceQuery,
        baseOutput,
        effectiveAccessContext,
        readinessQuery,
        readinessResponse,
      });
      if (!explanationServiceResult.ok) {
        return explanationServiceResult.failure;
      }

      const themeServiceResponse = explanationServiceResult.response;
      if (themeServiceResponse.service_status !== 'served') {
        return {
          ...readinessBlockedOutput,
          dependency_stage: 'service_not_served',
          reason_codes: normalizeReasonCodes(
            themeServiceResponse.explanation_object?.reason_codes,
            `runtime.service.${themeServiceResponse.service_status}`,
          ),
          theme_service_query: explanationServiceQuery,
          theme_service_response: themeServiceResponse,
        };
      }

      return {
        ...readinessBlockedOutput,
        dependency_stage: 'served',
        theme_service_query: explanationServiceQuery,
        theme_service_response: themeServiceResponse,
      };
    }

    let explanationServiceResponse = null;
    const explanationServiceResult = await queryValidatedThemeService({
      dataPlatformClient,
      query: explanationServiceQuery,
      baseOutput,
      effectiveAccessContext,
      readinessQuery,
      readinessResponse,
    });
    if (explanationServiceResult.ok && explanationServiceResult.response.service_status === 'served') {
      explanationServiceResponse = explanationServiceResult.response;
    }

    return {
      ...readinessBlockedOutput,
      dependency_stage: 'readiness_blocked',
      reason_codes: normalizeReasonCodes(
        [
          ...readinessResponse.reason_codes,
          ...readinessBlockedOutput.reason_codes,
        ],
        `runtime.readiness.${readinessResponse.readiness_status}`,
      ),
      explanation_service_query: explanationServiceQuery,
      explanation_service_response: explanationServiceResponse,
    };
  }

  const themeServiceQuery = buildThemeServiceQuery({
    interactionContext,
    executionPlan,
    effectiveAccessContext,
    accessDecision,
    readinessResponse,
  });

  const themeServiceResult = await queryValidatedThemeService({
    dataPlatformClient,
    query: themeServiceQuery,
    baseOutput,
    effectiveAccessContext,
    readinessQuery,
    readinessResponse,
  });
  if (!themeServiceResult.ok) {
    return themeServiceResult.failure;
  }
  const themeServiceResponse = themeServiceResult.response;

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
      access_decision_status: accessDecision.decision_status,
      restriction_codes: uniqueCodes(accessDecision.restriction_codes),
      obligation_codes: uniqueCodes(accessDecision.obligation_codes),
    };
  }

  return {
    ...baseOutput,
    effective_access_context: effectiveAccessContext,
    dependency_stage: 'served',
    reason_codes: normalizeReasonCodes(
      accessDecision.reason_codes,
      accessDecision.decision_status === 'restricted' ? 'runtime.access.restricted' : null,
    ),
    readiness_query: readinessQuery,
    readiness_response: readinessResponse,
    theme_service_query: themeServiceQuery,
    theme_service_response: themeServiceResponse,
    access_decision_status: accessDecision.decision_status,
    restriction_codes: uniqueCodes(accessDecision.restriction_codes),
    obligation_codes: uniqueCodes(accessDecision.obligation_codes),
  };
}
