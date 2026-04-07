import test from 'node:test';
import assert from 'node:assert/strict';
import { runMilestoneBGuardedExecutionChain } from '../execution/runtime-chain-backbone.mjs';

const FIXED_NOW = '2026-04-06T08:00:00.000Z';

function buildAccessContextEnvelope(overrides = {}) {
  return {
    request_id: 'req-runtime-001',
    trace_ref: 'navly:trace:req-runtime-001',
    decision_ref: 'navly:decision:gate0-runtime-001',
    actor_ref: 'navly:actor:sample-store-manager',
    session_ref: 'navly:session:sample-session',
    conversation_ref: 'navly:conversation:sample-conversation',
    tenant_ref: 'navly:tenant:sample-retail',
    primary_scope_ref: 'navly:scope:store:sample-store-001',
    granted_scope_refs: ['navly:scope:store:sample-store-001'],
    granted_capability_ids: ['navly.store.daily_overview'],
    issued_at: FIXED_NOW,
    expires_at: '2026-04-06T09:00:00.000Z',
    ...overrides,
  };
}

function buildRuntimeRequestEnvelope(overrides = {}) {
  return {
    request_id: 'req-runtime-001',
    ingress_ref: 'ingress-wecom-001',
    trace_ref: 'navly:trace:req-runtime-001',
    channel_kind: 'wecom',
    message_mode: 'direct_message',
    user_input_text: '帮我看下门店日报',
    structured_input_slots: {},
    requested_capability_id: 'navly.store.daily_overview',
    requested_service_object_id: null,
    target_scope_hint: 'navly:scope:store:sample-store-001',
    target_business_date_hint: '2026-04-06',
    response_channel_capabilities: {
      rich_text: true,
    },
    access_context_envelope: buildAccessContextEnvelope(),
    decision_ref: 'navly:decision:gate0-runtime-001',
    delivery_hint: {
      preferred_format: 'summary',
    },
    ...overrides,
  };
}

function buildAccessDecision({ request, status = 'allow', reasonCodes = [], obligationCodes = [] }) {
  return {
    decision_ref: `navly:decision:capability-${status}-001`,
    request_id: request.request_id,
    trace_ref: 'navly:trace:req-runtime-001',
    decision_status: status,
    actor_ref: 'navly:actor:sample-store-manager',
    session_ref: 'navly:session:sample-session',
    target_capability_id: request.requested_capability_id,
    target_scope_ref: request.requested_scope_ref,
    reason_codes: reasonCodes,
    restriction_codes: [],
    obligation_codes: obligationCodes,
    decided_at: FIXED_NOW,
    expires_at: '2026-04-06T09:00:00.000Z',
  };
}

function createAuthKernelClient({ decisionStatus = 'allow', reasonCodes = [], obligationCodes = [] } = {}) {
  const calls = [];

  return {
    calls,
    async evaluateCapabilityAccess(request) {
      calls.push(request);
      return {
        access_decision: buildAccessDecision({
          request,
          status: decisionStatus,
          reasonCodes,
          obligationCodes,
        }),
      };
    },
  };
}

function createDataPlatformClient({ readinessStatus = 'ready', readinessReasonCodes = [], serviceStatus = 'served', serviceReasonCodes = [] } = {}) {
  const readinessCalls = [];
  const serviceCalls = [];

  return {
    readinessCalls,
    serviceCalls,
    async queryCapabilityReadiness(query) {
      readinessCalls.push(query);
      return {
        request_id: query.request_id,
        trace_ref: query.trace_ref,
        capability_id: query.capability_id,
        readiness_status: readinessStatus,
        evaluated_scope_ref: query.target_scope_ref,
        requested_business_date: query.target_business_date,
        latest_usable_business_date: '2026-04-05',
        reason_codes: readinessReasonCodes,
        blocking_dependencies: [],
        state_trace_refs: ['navly:state-trace:readiness:sample'],
        run_trace_refs: ['navly:run-trace:ingestion:sample'],
        evaluated_at: FIXED_NOW,
      };
    },
    async queryThemeService(query) {
      serviceCalls.push(query);
      return {
        request_id: query.request_id,
        trace_ref: query.trace_ref,
        capability_id: query.capability_id,
        service_object_id: query.service_object_id,
        service_status: serviceStatus,
        service_object: {
          summary: 'store daily overview',
          total_sales: 12345,
        },
        data_window: {
          from: query.target_business_date,
          to: query.target_business_date,
        },
        explanation_object: serviceStatus === 'served'
          ? undefined
          : {
            capability_id: query.capability_id,
            explanation_scope: 'service',
            reason_codes: serviceReasonCodes,
            state_trace_refs: ['navly:state-trace:service:sample'],
            run_trace_refs: ['navly:run-trace:service:sample'],
          },
        state_trace_refs: ['navly:state-trace:service:sample'],
        run_trace_refs: ['navly:run-trace:service:sample'],
        served_at: FIXED_NOW,
      };
    },
  };
}

test('happy path closes route + access + readiness + service + runtime_result_envelope', async () => {
  const authKernelClient = createAuthKernelClient();
  const dataPlatformClient = createDataPlatformClient();

  const runtimeRequestEnvelope = buildRuntimeRequestEnvelope({
    requested_service_object_id: 'navly.service.store.unsupported_candidate',
    structured_input_slots: {
      freshness_mode: 'latest_usable',
    },
  });

  const result = await runMilestoneBGuardedExecutionChain({
    runtimeRequestEnvelope,
    authKernelClient,
    dataPlatformClient,
    now: FIXED_NOW,
  });

  assert.equal(result.capability_route_result.route_status, 'resolved');
  assert.equal(result.runtime_execution_plan.selected_service_object_id, 'navly.service.store.daily_overview');
  assert.equal(result.runtime_result_envelope.result_status, 'answered');
  assert.equal(result.runtime_result_envelope.selected_capability_id, 'navly.store.daily_overview');
  assert.equal(result.runtime_result_envelope.selected_service_object_id, 'navly.service.store.daily_overview');
  assert.ok(result.runtime_result_envelope.reason_codes.includes('runtime.route.service_binding_defaulted'));

  assert.equal(authKernelClient.calls.length, 1);
  assert.equal(dataPlatformClient.readinessCalls.length, 1);
  assert.equal(dataPlatformClient.serviceCalls.length, 1);
  assert.equal(dataPlatformClient.serviceCalls[0].target_business_date, '2026-04-05');
});

test('happy path without route or dependency warnings preserves empty reason_codes', async () => {
  const authKernelClient = createAuthKernelClient();
  const dataPlatformClient = createDataPlatformClient();

  const result = await runMilestoneBGuardedExecutionChain({
    runtimeRequestEnvelope: buildRuntimeRequestEnvelope({
      requested_service_object_id: 'navly.service.store.daily_overview',
    }),
    authKernelClient,
    dataPlatformClient,
    now: FIXED_NOW,
  });

  assert.equal(result.runtime_result_envelope.result_status, 'answered');
  assert.deepEqual(result.runtime_result_envelope.reason_codes, []);
});

test('unresolved route returns fallback without dependency calls', async () => {
  const authKernelClient = createAuthKernelClient();
  const dataPlatformClient = createDataPlatformClient();

  const runtimeRequestEnvelope = buildRuntimeRequestEnvelope({
    requested_capability_id: null,
    requested_service_object_id: null,
    user_input_text: '请问今天安排',
  });

  const result = await runMilestoneBGuardedExecutionChain({
    runtimeRequestEnvelope,
    authKernelClient,
    dataPlatformClient,
    now: FIXED_NOW,
  });

  assert.equal(result.capability_route_result.route_status, 'unresolved');
  assert.equal(result.runtime_result_envelope.result_status, 'fallback');
  assert.ok(result.runtime_result_envelope.reason_codes.includes('runtime.route.unresolved'));
  assert.equal(authKernelClient.calls.length, 0);
  assert.equal(dataPlatformClient.readinessCalls.length, 0);
  assert.equal(dataPlatformClient.serviceCalls.length, 0);
});

test('match token resolution ignores entries that do not opt into token matching', async () => {
  const authKernelClient = createAuthKernelClient();
  const dataPlatformClient = createDataPlatformClient();

  const routeRegistry = {
    registry_name: 'capability_route_registry',
    status: 'milestone_b_backbone',
    route_strategy: 'capability_first_then_service_object',
    entries: [
      {
        route_id: 'capability.navly.store.daily_overview.explicit_only',
        match_mode: 'explicit_capability_id',
        match_tokens: ['门店日报'],
        capability_id: 'navly.store.daily_overview',
        default_service_object_id: 'navly.service.store.daily_overview',
        supported_service_object_ids: ['navly.service.store.daily_overview'],
        status: 'implemented_milestone_b',
      },
    ],
    default_fallback: {
      result_status: 'fallback',
      reason_code: 'runtime.route.unresolved',
      next_action: 'request_capability_clarification',
      fallback_capability_id: 'navly.system.capability_explanation',
      fallback_service_object_id: 'navly.service.system.capability_explanation',
    },
  };

  const result = await runMilestoneBGuardedExecutionChain({
    runtimeRequestEnvelope: buildRuntimeRequestEnvelope({
      requested_capability_id: null,
      requested_service_object_id: null,
      user_input_text: '门店日报',
    }),
    authKernelClient,
    dataPlatformClient,
    routeRegistry,
    now: FIXED_NOW,
  });

  assert.equal(result.capability_route_result.route_status, 'unresolved');
  assert.equal(result.runtime_result_envelope.result_status, 'fallback');
  assert.equal(authKernelClient.calls.length, 0);
  assert.equal(dataPlatformClient.readinessCalls.length, 0);
});

test('access deny returns rejected and does not call readiness/service', async () => {
  const authKernelClient = createAuthKernelClient({
    decisionStatus: 'deny',
    reasonCodes: ['capability_not_granted'],
  });
  const dataPlatformClient = createDataPlatformClient();

  const result = await runMilestoneBGuardedExecutionChain({
    runtimeRequestEnvelope: buildRuntimeRequestEnvelope(),
    authKernelClient,
    dataPlatformClient,
    now: FIXED_NOW,
  });

  assert.equal(result.runtime_dependency_outcome.dependency_stage, 'access_denied');
  assert.equal(result.runtime_result_envelope.result_status, 'rejected');
  assert.ok(result.runtime_result_envelope.reason_codes.includes('capability_not_granted'));
  assert.equal(dataPlatformClient.readinessCalls.length, 0);
  assert.equal(dataPlatformClient.serviceCalls.length, 0);
});

test('access escalation returns escalated and does not call readiness/service', async () => {
  const authKernelClient = createAuthKernelClient({
    decisionStatus: 'escalation',
    reasonCodes: ['manual_review_needed'],
    obligationCodes: ['request_operator_confirmation'],
  });
  const dataPlatformClient = createDataPlatformClient();

  const result = await runMilestoneBGuardedExecutionChain({
    runtimeRequestEnvelope: buildRuntimeRequestEnvelope(),
    authKernelClient,
    dataPlatformClient,
    now: FIXED_NOW,
  });

  assert.equal(result.runtime_dependency_outcome.dependency_stage, 'access_escalated');
  assert.equal(result.runtime_result_envelope.result_status, 'escalated');
  assert.ok(result.runtime_result_envelope.escalation_action);
  assert.equal(dataPlatformClient.readinessCalls.length, 0);
  assert.equal(dataPlatformClient.serviceCalls.length, 0);
});

test('readiness pending returns fallback and skips theme service query', async () => {
  const authKernelClient = createAuthKernelClient();
  const dataPlatformClient = createDataPlatformClient({
    readinessStatus: 'pending',
    readinessReasonCodes: ['source_window_not_open'],
  });

  const result = await runMilestoneBGuardedExecutionChain({
    runtimeRequestEnvelope: buildRuntimeRequestEnvelope(),
    authKernelClient,
    dataPlatformClient,
    now: FIXED_NOW,
  });

  assert.equal(result.runtime_dependency_outcome.dependency_stage, 'readiness_blocked');
  assert.equal(result.runtime_result_envelope.result_status, 'fallback');
  assert.ok(result.runtime_result_envelope.reason_codes.includes('source_window_not_open'));
  assert.equal(dataPlatformClient.readinessCalls.length, 1);
  assert.equal(dataPlatformClient.serviceCalls.length, 0);
});

test('theme service scope mismatch returns fallback with service reason codes', async () => {
  const authKernelClient = createAuthKernelClient();
  const dataPlatformClient = createDataPlatformClient({
    serviceStatus: 'scope_mismatch',
    serviceReasonCodes: ['scope_out_of_contract'],
  });

  const result = await runMilestoneBGuardedExecutionChain({
    runtimeRequestEnvelope: buildRuntimeRequestEnvelope(),
    authKernelClient,
    dataPlatformClient,
    now: FIXED_NOW,
  });

  assert.equal(result.runtime_dependency_outcome.dependency_stage, 'service_not_served');
  assert.equal(result.runtime_result_envelope.result_status, 'fallback');
  assert.ok(result.runtime_result_envelope.reason_codes.includes('scope_out_of_contract'));
  assert.equal(dataPlatformClient.readinessCalls.length, 1);
  assert.equal(dataPlatformClient.serviceCalls.length, 1);
});

test('malformed auth access_decision fails closed with runtime_error', async () => {
  const authKernelClient = {
    calls: [],
    async evaluateCapabilityAccess(request) {
      this.calls.push(request);
      return {
        access_decision: {
          decision_ref: 'navly:decision:malformed-auth-001',
          request_id: request.request_id,
          trace_ref: 'navly:trace:req-runtime-001',
        },
      };
    },
  };
  const dataPlatformClient = createDataPlatformClient();

  const result = await runMilestoneBGuardedExecutionChain({
    runtimeRequestEnvelope: buildRuntimeRequestEnvelope(),
    authKernelClient,
    dataPlatformClient,
    now: FIXED_NOW,
  });

  assert.equal(result.runtime_dependency_outcome.dependency_stage, 'dependency_error');
  assert.equal(result.runtime_result_envelope.result_status, 'runtime_error');
  assert.ok(result.runtime_result_envelope.reason_codes.includes('runtime.dependency.auth_invalid_response'));
  assert.equal(dataPlatformClient.readinessCalls.length, 0);
  assert.equal(dataPlatformClient.serviceCalls.length, 0);
});

test('malformed readiness response fails closed with runtime_error', async () => {
  const authKernelClient = createAuthKernelClient();
  const dataPlatformClient = {
    readinessCalls: [],
    serviceCalls: [],
    async queryCapabilityReadiness(query) {
      this.readinessCalls.push(query);
      return {
        request_id: query.request_id,
        trace_ref: query.trace_ref,
        capability_id: query.capability_id,
      };
    },
    async queryThemeService(query) {
      this.serviceCalls.push(query);
      return {};
    },
  };

  const result = await runMilestoneBGuardedExecutionChain({
    runtimeRequestEnvelope: buildRuntimeRequestEnvelope(),
    authKernelClient,
    dataPlatformClient,
    now: FIXED_NOW,
  });

  assert.equal(result.runtime_dependency_outcome.dependency_stage, 'dependency_error');
  assert.equal(result.runtime_result_envelope.result_status, 'runtime_error');
  assert.ok(result.runtime_result_envelope.reason_codes.includes('runtime.dependency.readiness_invalid_response'));
  assert.equal(dataPlatformClient.readinessCalls.length, 1);
  assert.equal(dataPlatformClient.serviceCalls.length, 0);
});

test('malformed theme service response fails closed with runtime_error', async () => {
  const authKernelClient = createAuthKernelClient();
  const dataPlatformClient = {
    readinessCalls: [],
    serviceCalls: [],
    async queryCapabilityReadiness(query) {
      this.readinessCalls.push(query);
      return {
        request_id: query.request_id,
        trace_ref: query.trace_ref,
        capability_id: query.capability_id,
        readiness_status: 'ready',
        evaluated_scope_ref: query.target_scope_ref,
        requested_business_date: query.target_business_date,
        latest_usable_business_date: '2026-04-05',
        reason_codes: [],
        blocking_dependencies: [],
        state_trace_refs: ['navly:state-trace:readiness:sample'],
        run_trace_refs: ['navly:run-trace:ingestion:sample'],
        evaluated_at: FIXED_NOW,
      };
    },
    async queryThemeService(query) {
      this.serviceCalls.push(query);
      return {
        request_id: query.request_id,
        trace_ref: query.trace_ref,
        capability_id: query.capability_id,
        service_object_id: query.service_object_id,
      };
    },
  };

  const result = await runMilestoneBGuardedExecutionChain({
    runtimeRequestEnvelope: buildRuntimeRequestEnvelope(),
    authKernelClient,
    dataPlatformClient,
    now: FIXED_NOW,
  });

  assert.equal(result.runtime_dependency_outcome.dependency_stage, 'dependency_error');
  assert.equal(result.runtime_result_envelope.result_status, 'runtime_error');
  assert.ok(result.runtime_result_envelope.reason_codes.includes('runtime.dependency.service_invalid_response'));
  assert.equal(dataPlatformClient.readinessCalls.length, 1);
  assert.equal(dataPlatformClient.serviceCalls.length, 1);
});

test('missing access context fails closed with runtime_error', async () => {
  const authKernelClient = createAuthKernelClient();
  const dataPlatformClient = createDataPlatformClient();

  const runtimeRequestEnvelope = buildRuntimeRequestEnvelope();
  delete runtimeRequestEnvelope.access_context_envelope;

  const result = await runMilestoneBGuardedExecutionChain({
    runtimeRequestEnvelope,
    authKernelClient,
    dataPlatformClient,
    now: FIXED_NOW,
  });

  assert.equal(result.runtime_result_envelope.result_status, 'runtime_error');
  assert.ok(result.runtime_result_envelope.reason_codes.includes('runtime.ingress.validation_failed'));
  assert.equal(authKernelClient.calls.length, 0);
  assert.equal(dataPlatformClient.readinessCalls.length, 0);
  assert.equal(dataPlatformClient.serviceCalls.length, 0);
});
