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

function buildCapabilityAccessRequest({ interactionContext, executionPlan }) {
  return {
    request_id: interactionContext.request_id,
    session_ref: interactionContext.access_context_envelope.session_ref,
    conversation_ref: interactionContext.access_context_envelope.conversation_ref,
    prior_decision_ref: interactionContext.decision_ref,
    requested_capability_id: executionPlan.selected_capability_id,
    requested_scope_ref: executionPlan.target_scope_ref,
    requested_service_object_id: executionPlan.selected_service_object_id,
    operation_kind: 'read',
    runtime_trace_ref: interactionContext.runtime_trace_ref,
  };
}

function resolveEffectiveAccessContext({ interactionContext, capabilityAccessResponse }) {
  if (capabilityAccessResponse?.access_context_envelope) {
    return validateAccessContextEnvelopeShape(capabilityAccessResponse.access_context_envelope);
  }

  return interactionContext.access_context_envelope;
}

function buildReadinessQuery({ interactionContext, executionPlan, effectiveAccessContext, accessDecision }) {
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
      dependency_stage: 'dependency_error',
      reason_codes: ['runtime.dependency.auth_missing_access_decision'],
      error_message: 'auth dependency did not return access_decision',
      capability_access_request: capabilityAccessRequest,
      capability_access_response: capabilityAccessResponse ?? null,
      effective_access_context: interactionContext.access_context_envelope,
      readiness_query: null,
      readiness_response: null,
      theme_service_query: null,
      theme_service_response: null,
    };
  }

  const accessDecision = validateAccessDecisionShape(capabilityAccessResponse.access_decision);
  const effectiveAccessContext = resolveEffectiveAccessContext({
    interactionContext,
    capabilityAccessResponse,
  });

  const baseOutput = {
    capability_access_request: capabilityAccessRequest,
    capability_access_response: capabilityAccessResponse,
    effective_access_context: effectiveAccessContext,
    readiness_query: null,
    readiness_response: null,
    theme_service_query: null,
    theme_service_response: null,
    reason_codes: [],
    error_message: null,
  };

  if (accessDecision.decision_status === 'deny') {
    return {
      ...baseOutput,
      dependency_stage: 'access_denied',
      reason_codes: normalizeReasonCodes(accessDecision.reason_codes, 'runtime.access.denied'),
    };
  }

  if (accessDecision.decision_status === 'escalation') {
    return {
      ...baseOutput,
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
    return {
      ...baseOutput,
      dependency_stage: 'dependency_error',
      reason_codes: ['runtime.dependency.readiness_error'],
      error_message: error?.message ?? 'readiness dependency call failed',
      readiness_query: readinessQuery,
    };
  }

  readinessResponse = validateReadinessResponseShape(readinessResponse);

  if (readinessResponse.readiness_status !== 'ready') {
    return {
      ...baseOutput,
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
    return {
      ...baseOutput,
      dependency_stage: 'dependency_error',
      reason_codes: ['runtime.dependency.service_error'],
      error_message: error?.message ?? 'theme service dependency call failed',
      readiness_query: readinessQuery,
      readiness_response: readinessResponse,
      theme_service_query: themeServiceQuery,
    };
  }

  themeServiceResponse = validateThemeServiceResponseShape(themeServiceResponse);

  if (themeServiceResponse.service_status !== 'served') {
    return {
      ...baseOutput,
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
    dependency_stage: 'served',
    reason_codes: [],
    readiness_query: readinessQuery,
    readiness_response: readinessResponse,
    theme_service_query: themeServiceQuery,
    theme_service_response: themeServiceResponse,
  };
}
