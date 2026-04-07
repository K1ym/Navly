import {
  ensureRuntimeResultStatus,
  filterTraceRefsByFamily,
  normalizeReasonCodes,
} from '../contracts/shared-contract-alignment.mjs';

const DEFAULT_FALLBACK_CAPABILITY_ID = 'navly.system.capability_explanation';
const DEFAULT_FALLBACK_SERVICE_OBJECT_ID = 'navly.service.system.capability_explanation';

function selectResultStatus({ ingressError, routeResult, dependencyOutcome }) {
  if (ingressError) {
    return 'runtime_error';
  }

  if (!routeResult || routeResult.route_status !== 'resolved') {
    return 'fallback';
  }

  switch (dependencyOutcome?.dependency_stage) {
    case 'served':
      return 'answered';
    case 'access_denied':
      return 'rejected';
    case 'access_escalated':
      return 'escalated';
    case 'readiness_blocked':
      return 'fallback';
    case 'service_not_served':
      return 'fallback';
    case 'dependency_error':
      return 'runtime_error';
    default:
      return 'runtime_error';
  }
}

function collectReasonCodes({ ingressError, routeResult, dependencyOutcome }) {
  if (ingressError) {
    return normalizeReasonCodes([ingressError.reason_code], 'runtime.ingress.validation_failed');
  }

  const routeReasonCodes = routeResult?.reason_codes ?? [];
  const dependencyReasonCodes = dependencyOutcome?.reason_codes ?? [];
  const combinedReasonCodes = normalizeReasonCodes([...routeReasonCodes, ...dependencyReasonCodes], null);
  if (combinedReasonCodes.length > 0) {
    return combinedReasonCodes;
  }

  if (!routeResult || routeResult.route_status !== 'resolved') {
    return normalizeReasonCodes(routeReasonCodes, routeResult?.fallback_plan?.reason_code ?? 'runtime.route.unresolved');
  }

  if (!dependencyOutcome || dependencyOutcome.dependency_stage === 'served') {
    return [];
  }

  return normalizeReasonCodes(dependencyReasonCodes, 'runtime.unclassified');
}

function buildAnswerFragments({ resultStatus, routeResult, dependencyOutcome }) {
  if (resultStatus !== 'answered') {
    return [];
  }

  const themeServiceResponse = dependencyOutcome?.theme_service_response;
  return [
    {
      fragment_type: 'service_object',
      capability_id: routeResult.selected_capability_id,
      service_object_id: routeResult.selected_service_object_id,
      data_window: themeServiceResponse?.data_window ?? {},
      service_object: themeServiceResponse?.service_object ?? {},
    },
  ];
}

function buildExplanationFragments({ resultStatus, routeResult, dependencyOutcome, ingressError }) {
  if (resultStatus === 'answered') {
    return [];
  }

  if (ingressError) {
    return [
      {
        fragment_type: 'runtime_error',
        summary_key: 'runtime.ingress.validation_failed',
        detail: ingressError.message,
      },
    ];
  }

  if (!routeResult || routeResult.route_status !== 'resolved') {
    return [
      {
        fragment_type: 'route_fallback',
        summary_key: routeResult?.fallback_plan?.next_action ?? 'request_capability_clarification',
        reason_codes: routeResult?.reason_codes ?? ['runtime.route.unresolved'],
      },
    ];
  }

  return [
    {
      fragment_type: 'guarded_execution',
      dependency_stage: dependencyOutcome?.dependency_stage ?? 'unknown',
      reason_codes: dependencyOutcome?.reason_codes ?? ['runtime.unclassified'],
      error_message: dependencyOutcome?.error_message ?? null,
      readiness_status: dependencyOutcome?.readiness_response?.readiness_status ?? null,
      service_status: dependencyOutcome?.theme_service_response?.service_status ?? null,
      access_decision_status: dependencyOutcome?.capability_access_response?.access_decision?.decision_status ?? null,
    },
  ];
}

function buildEscalationAction({ resultStatus, dependencyOutcome }) {
  if (resultStatus !== 'escalated') {
    return null;
  }

  return {
    action_kind: 'request_authorization_escalation',
    reason_codes: dependencyOutcome?.reason_codes ?? ['runtime.access.escalation'],
    obligation_codes: dependencyOutcome?.capability_access_response?.access_decision?.obligation_codes ?? [],
  };
}

function selectCapabilityId(routeResult) {
  return routeResult?.selected_capability_id ?? DEFAULT_FALLBACK_CAPABILITY_ID;
}

function selectServiceObjectId(routeResult) {
  return routeResult?.selected_service_object_id ?? DEFAULT_FALLBACK_SERVICE_OBJECT_ID;
}

function collectDependencyTraceRefs(dependencyOutcome) {
  if (!dependencyOutcome) {
    return [];
  }

  return filterTraceRefsByFamily(
    [dependencyOutcome.capability_access_response?.access_decision?.trace_ref],
    [dependencyOutcome.readiness_response?.trace_ref],
    dependencyOutcome.readiness_response?.state_trace_refs,
    dependencyOutcome.readiness_response?.run_trace_refs,
    [dependencyOutcome.theme_service_response?.trace_ref],
    dependencyOutcome.theme_service_response?.state_trace_refs,
    dependencyOutcome.theme_service_response?.run_trace_refs,
  );
}

export function assembleRuntimeResultEnvelope({
  runtimeIdentity,
  routeResult,
  dependencyOutcome,
  ingressError = null,
}) {
  const resultStatus = ensureRuntimeResultStatus(selectResultStatus({
    ingressError,
    routeResult,
    dependencyOutcome,
  }));

  const reasonCodes = collectReasonCodes({ ingressError, routeResult, dependencyOutcome });

  const traceRefs = filterTraceRefsByFamily(
    [runtimeIdentity.trace_ref, runtimeIdentity.runtime_trace_ref],
    collectDependencyTraceRefs(dependencyOutcome),
  );

  return {
    request_id: runtimeIdentity.request_id,
    runtime_trace_ref: runtimeIdentity.runtime_trace_ref,
    result_status: resultStatus,
    selected_capability_id: selectCapabilityId(routeResult),
    selected_service_object_id: selectServiceObjectId(routeResult),
    answer_fragments: buildAnswerFragments({ resultStatus, routeResult, dependencyOutcome }),
    explanation_fragments: buildExplanationFragments({
      resultStatus,
      routeResult,
      dependencyOutcome,
      ingressError,
    }),
    escalation_action: buildEscalationAction({ resultStatus, dependencyOutcome }),
    reason_codes: reasonCodes,
    trace_refs: traceRefs,
    delivery_hints: {
      channel_kind: runtimeIdentity.channel_kind,
      message_mode: runtimeIdentity.message_mode,
      response_channel_capabilities: runtimeIdentity.response_channel_capabilities,
      delivery_hint: runtimeIdentity.delivery_hint ?? {},
    },
  };
}
