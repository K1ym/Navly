import { assembleRuntimeResultEnvelope } from '../answering/runtime-result-backbone.mjs';
import { buildRuntimeInteractionContext } from '../ingress/runtime-ingress-backbone.mjs';
import { buildRuntimeOutcomeEvent } from '../outcome/runtime-outcome-event-backbone.mjs';
import {
  buildRuntimeExecutionPlan,
  loadCapabilityRouteRegistry,
  resolveCapabilityRoute,
} from '../routing/capability-route-backbone.mjs';
import { runGuardedExecution } from './guarded-execution-backbone.mjs';
import { buildRuntimeTraceRef } from '../contracts/shared-contract-alignment.mjs';

function buildFallbackRuntimeIdentity(runtimeRequestEnvelope, now) {
  const requestId = runtimeRequestEnvelope?.request_id ?? `runtime-missing-request-${now.slice(0, 10)}`;
  const traceRef = runtimeRequestEnvelope?.trace_ref ?? 'navly:trace:runtime-missing-trace';
  const decisionRef = runtimeRequestEnvelope?.decision_ref ?? 'navly:decision:runtime-missing-decision';

  return {
    request_id: requestId,
    trace_ref: traceRef,
    runtime_trace_ref: buildRuntimeTraceRef(requestId, traceRef),
    decision_ref: decisionRef,
    channel_kind: runtimeRequestEnvelope?.channel_kind ?? 'unknown',
    message_mode: runtimeRequestEnvelope?.message_mode ?? 'unknown',
    response_channel_capabilities: runtimeRequestEnvelope?.response_channel_capabilities ?? {},
    delivery_hint: runtimeRequestEnvelope?.delivery_hint ?? {},
  };
}

function routeFallbackFromScopeError(routeRegistry, error) {
  return {
    route_status: 'unresolved',
    route_id: null,
    selected_capability_id: routeRegistry.default_fallback.fallback_capability_id,
    selected_service_object_id: routeRegistry.default_fallback.fallback_service_object_id,
    reason_codes: ['runtime.route.scope_unavailable'],
    fallback_plan: {
      ...routeRegistry.default_fallback,
      scope_error: error?.message ?? 'scope unavailable in granted scope refs',
    },
  };
}

export async function runMilestoneBGuardedExecutionChain({
  runtimeRequestEnvelope,
  authKernelClient,
  dataPlatformClient,
  routeRegistry = loadCapabilityRouteRegistry(),
  now = new Date().toISOString(),
}) {
  let runtimeIdentity = buildFallbackRuntimeIdentity(runtimeRequestEnvelope, now);
  let interactionContext = null;
  let routeResult = null;
  let executionPlan = null;
  let dependencyOutcome = null;
  let ingressError = null;

  try {
    interactionContext = buildRuntimeInteractionContext({ runtimeRequestEnvelope, now });
    runtimeIdentity = {
      request_id: interactionContext.request_id,
      trace_ref: interactionContext.trace_ref,
      runtime_trace_ref: interactionContext.runtime_trace_ref,
      decision_ref: interactionContext.decision_ref,
      channel_kind: interactionContext.channel_kind,
      message_mode: interactionContext.message_mode,
      response_channel_capabilities: interactionContext.response_channel_capabilities,
      delivery_hint: interactionContext.delivery_hint,
    };
  } catch (error) {
    ingressError = {
      reason_code: 'runtime.ingress.validation_failed',
      message: error?.message ?? 'invalid runtime_request_envelope',
    };
  }

  if (!ingressError) {
    routeResult = resolveCapabilityRoute({
      interactionContext,
      routeRegistry,
    });

    if (routeResult.route_status === 'resolved') {
      try {
        executionPlan = buildRuntimeExecutionPlan({
          interactionContext,
          routeResult,
        });
      } catch (error) {
        routeResult = routeFallbackFromScopeError(routeRegistry, error);
      }
    }

    if (routeResult.route_status === 'resolved' && executionPlan) {
      try {
        dependencyOutcome = await runGuardedExecution({
          interactionContext,
          executionPlan,
          authKernelClient,
          dataPlatformClient,
        });
      } catch (error) {
        dependencyOutcome = {
          dependency_stage: 'dependency_error',
          reason_codes: ['runtime.dependency.unhandled_error'],
          error_message: error?.message ?? 'unexpected guarded execution failure',
          capability_access_request: null,
          capability_access_response: null,
          effective_access_context: interactionContext.access_context_envelope,
          readiness_query: null,
          readiness_response: null,
          theme_service_query: null,
          theme_service_response: null,
        };
      }
    }
  }

  const runtimeResultEnvelope = assembleRuntimeResultEnvelope({
    runtimeIdentity,
    routeResult,
    dependencyOutcome,
    ingressError,
  });

  const runtimeOutcomeEvent = buildRuntimeOutcomeEvent({
    runtimeIdentity,
    runtimeResultEnvelope,
    now,
  });

  return {
    runtime_interaction_context: interactionContext,
    capability_route_result: routeResult,
    runtime_execution_plan: executionPlan,
    runtime_dependency_outcome: dependencyOutcome,
    runtime_result_envelope: runtimeResultEnvelope,
    runtime_outcome_event: runtimeOutcomeEvent,
  };
}
