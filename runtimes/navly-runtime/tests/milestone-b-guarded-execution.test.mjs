import test from 'node:test';
import assert from 'node:assert/strict';
import { runMilestoneBGuardedExecutionChain } from '../execution/runtime-chain-backbone.mjs';

const FIXED_NOW = '2026-04-06T08:00:00.000Z';
const EXPLANATION_SERVICE_OBJECT_ID = 'navly.service.system.capability_explanation';

const capabilityServiceBinding = {
  'navly.store.member_insight': 'navly.service.store.member_insight',
  'navly.store.daily_overview': 'navly.service.store.daily_overview',
  'navly.store.staff_board': 'navly.service.store.staff_board',
  'navly.store.finance_summary': 'navly.service.store.finance_summary',
};

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
    granted_capability_ids: [
      'navly.store.member_insight',
      'navly.store.daily_overview',
      'navly.store.staff_board',
      'navly.store.finance_summary',
      'navly.system.capability_explanation',
    ],
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
    user_input_text: '帮我看下会员洞察',
    structured_input_slots: {},
    requested_capability_id: 'navly.store.member_insight',
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

function buildAccessDecision({
  request,
  status = 'allow',
  reasonCodes = [],
  restrictionCodes = [],
  obligationCodes = [],
  targetScopeRef = null,
}) {
  return {
    decision_ref: `navly:decision:capability-${status}-001`,
    request_id: request.request_id,
    trace_ref: 'navly:trace:req-runtime-001',
    decision_status: status,
    actor_ref: 'navly:actor:sample-store-manager',
    session_ref: 'navly:session:sample-session',
    target_capability_id: request.requested_capability_id,
    target_scope_ref: targetScopeRef ?? request.requested_scope_ref,
    reason_codes: reasonCodes,
    restriction_codes: restrictionCodes,
    obligation_codes: obligationCodes,
    decided_at: FIXED_NOW,
    expires_at: '2026-04-06T09:00:00.000Z',
  };
}

function createAuthKernelClient({
  decisionStatus = 'allow',
  reasonCodes = [],
  restrictionCodes = [],
  obligationCodes = [],
  effectiveAccessContext = null,
  targetScopeRef = null,
} = {}) {
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
          restrictionCodes,
          obligationCodes,
          targetScopeRef,
        }),
        access_context_envelope: effectiveAccessContext,
      };
    },
  };
}

function buildServedServiceObject(capabilityId, serviceObjectId, targetScopeRef, targetBusinessDate) {
  switch (serviceObjectId) {
    case 'navly.service.store.daily_overview':
      return {
        capability_id: capabilityId,
        service_object_id: serviceObjectId,
        target_scope_ref: targetScopeRef,
        target_business_date: targetBusinessDate,
        business_day_boundary_policy: {
          business_day_boundary_local_time: '03:00:00',
          timezone: 'Asia/Shanghai',
        },
        published_service_object_ids: [
          'navly.service.store.member_insight',
          'navly.service.store.staff_board',
          'navly.service.store.finance_summary',
        ],
        member_insight: { customer_count: 1 },
        staff_board: { staff_count: 2 },
        finance_summary: { account_trade_count: 1 },
      };
    case 'navly.service.store.staff_board':
      return {
        capability_id: capabilityId,
        service_object_id: serviceObjectId,
        target_scope_ref: targetScopeRef,
        target_business_date: targetBusinessDate,
        staff_count: 2,
        on_duty_count: 1,
      };
    case 'navly.service.store.finance_summary':
      return {
        capability_id: capabilityId,
        service_object_id: serviceObjectId,
        target_scope_ref: targetScopeRef,
        target_business_date: targetBusinessDate,
        recharge_bill_count: 1,
        account_trade_count: 1,
      };
    default:
      return {
        capability_id: capabilityId,
        service_object_id: serviceObjectId,
        target_scope_ref: targetScopeRef,
        target_business_date: targetBusinessDate,
        summary: 'store member insight',
        customer_count: 11,
      };
  }
}

function buildExplanationServiceObject({
  capabilityId,
  targetScopeRef,
  targetBusinessDate,
  readinessStatus,
  reasonCodes,
  serviceStatus,
}) {
  return {
    capability_id: capabilityId,
    service_object_id: EXPLANATION_SERVICE_OBJECT_ID,
    target_scope_ref: targetScopeRef,
    target_business_date: targetBusinessDate,
    latest_usable_business_date: targetBusinessDate,
    readiness_status: readinessStatus,
    theme_service_status: serviceStatus,
    reason_codes: reasonCodes,
    blocking_dependencies: [],
    explanation_fragments: [
      {
        fragment_kind: 'readiness_status',
        value: readinessStatus,
      },
      ...reasonCodes.map((reasonCode) => ({
        fragment_kind: 'reason_code',
        value: reasonCode,
      })),
    ],
    recommended_fallback_action: readinessStatus === 'ready'
      ? 'consume_theme_service'
      : 'inspect_trace_refs',
    next_recheck_hint: readinessStatus === 'ready'
      ? 'recheck_not_required'
      : 'recheck_after_manual_investigation',
  };
}

function createDataPlatformClient({
  readinessStatus = 'ready',
  readinessReasonCodes = [],
  serviceStatus = 'served',
  serviceReasonCodes = [],
  latestUsableBusinessDate = '2026-04-05',
  explanationServiceStatus = 'served',
  explanationReasonCodes = null,
} = {}) {
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
        latest_usable_business_date: latestUsableBusinessDate,
        reason_codes: readinessReasonCodes,
        blocking_dependencies: [],
        state_trace_refs: ['navly:state-trace:readiness:sample'],
        run_trace_refs: ['navly:run-trace:ingestion:sample'],
        evaluated_at: FIXED_NOW,
      };
    },
    async queryThemeService(query) {
      serviceCalls.push(query);
      if (query.service_object_id === EXPLANATION_SERVICE_OBJECT_ID) {
        const reasonCodes = explanationReasonCodes ?? readinessReasonCodes;
        return {
          request_id: query.request_id,
          trace_ref: query.trace_ref,
          capability_id: query.capability_id,
          service_object_id: EXPLANATION_SERVICE_OBJECT_ID,
          service_status: explanationServiceStatus,
          service_object: explanationServiceStatus === 'served'
            ? buildExplanationServiceObject({
              capabilityId: query.capability_id,
              targetScopeRef: query.target_scope_ref,
              targetBusinessDate: query.target_business_date,
              readinessStatus,
              reasonCodes,
              serviceStatus,
            })
            : {},
          data_window: {
            from: query.target_business_date,
            to: query.target_business_date,
          },
          explanation_object: {
            capability_id: query.capability_id,
            explanation_scope: readinessStatus === 'ready' ? 'service' : 'readiness',
            reason_codes: reasonCodes,
            state_trace_refs: ['navly:state-trace:explanation:sample'],
            run_trace_refs: ['navly:run-trace:explanation:sample'],
          },
          state_trace_refs: ['navly:state-trace:explanation:sample'],
          run_trace_refs: ['navly:run-trace:explanation:sample'],
          served_at: FIXED_NOW,
        };
      }

      return {
        request_id: query.request_id,
        trace_ref: query.trace_ref,
        capability_id: query.capability_id,
        service_object_id: query.service_object_id,
        service_status: serviceStatus,
        service_object: serviceStatus === 'served'
          ? buildServedServiceObject(
            query.capability_id,
            query.service_object_id,
            query.target_scope_ref,
            query.target_business_date,
          )
          : {},
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
  assert.equal(result.runtime_execution_plan.selected_service_object_id, 'navly.service.store.member_insight');
  assert.equal(result.runtime_result_envelope.result_status, 'answered');
  assert.equal(result.runtime_result_envelope.selected_capability_id, 'navly.store.member_insight');
  assert.equal(result.runtime_result_envelope.selected_service_object_id, 'navly.service.store.member_insight');
  assert.ok(result.runtime_result_envelope.reason_codes.includes('runtime.route.service_binding_defaulted'));
  assert.ok(result.runtime_result_envelope.trace_refs.every((ref) => !ref.startsWith('navly:decision:')));
  assert.ok(result.runtime_result_envelope.trace_refs.every((ref) => (
    ref.startsWith('navly:trace:')
    || ref.startsWith('navly:state-trace:')
    || ref.startsWith('navly:run-trace:')
    || ref.startsWith('navly:runtime-trace:')
  )));

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
      requested_service_object_id: 'navly.service.store.member_insight',
    }),
    authKernelClient,
    dataPlatformClient,
    now: FIXED_NOW,
  });

  assert.equal(result.runtime_result_envelope.result_status, 'answered');
  assert.deepEqual(result.runtime_result_envelope.reason_codes, []);
});

test('daily_overview explicit route closes through the shared guarded execution path', async () => {
  const authKernelClient = createAuthKernelClient();
  const dataPlatformClient = createDataPlatformClient();

  const result = await runMilestoneBGuardedExecutionChain({
    runtimeRequestEnvelope: buildRuntimeRequestEnvelope({
      user_input_text: '请给我今天的门店日报',
      requested_capability_id: 'navly.store.daily_overview',
      requested_service_object_id: 'navly.service.store.daily_overview',
    }),
    authKernelClient,
    dataPlatformClient,
    now: FIXED_NOW,
  });

  assert.equal(result.capability_route_result.selected_capability_id, 'navly.store.daily_overview');
  assert.equal(result.runtime_result_envelope.selected_service_object_id, 'navly.service.store.daily_overview');
  assert.equal(result.runtime_result_envelope.result_status, 'answered');
  assert.equal(dataPlatformClient.serviceCalls[0].service_object_id, 'navly.service.store.daily_overview');
});

test('staff_board token route closes through the shared guarded execution path', async () => {
  const authKernelClient = createAuthKernelClient();
  const dataPlatformClient = createDataPlatformClient();

  const result = await runMilestoneBGuardedExecutionChain({
    runtimeRequestEnvelope: buildRuntimeRequestEnvelope({
      user_input_text: '员工看板',
      requested_capability_id: null,
      requested_service_object_id: null,
    }),
    authKernelClient,
    dataPlatformClient,
    now: FIXED_NOW,
  });

  assert.equal(result.capability_route_result.selected_capability_id, 'navly.store.staff_board');
  assert.equal(result.runtime_result_envelope.selected_service_object_id, 'navly.service.store.staff_board');
  assert.equal(result.runtime_result_envelope.result_status, 'answered');
});

test('finance_summary can explicitly request the capability_explanation companion service', async () => {
  const authKernelClient = createAuthKernelClient();
  const dataPlatformClient = createDataPlatformClient();

  const result = await runMilestoneBGuardedExecutionChain({
    runtimeRequestEnvelope: buildRuntimeRequestEnvelope({
      user_input_text: '解释一下财务汇总',
      requested_capability_id: 'navly.store.finance_summary',
      requested_service_object_id: EXPLANATION_SERVICE_OBJECT_ID,
    }),
    authKernelClient,
    dataPlatformClient,
    now: FIXED_NOW,
  });

  assert.equal(result.capability_route_result.selected_capability_id, 'navly.store.finance_summary');
  assert.equal(result.capability_route_result.selected_service_object_id, EXPLANATION_SERVICE_OBJECT_ID);
  assert.equal(result.runtime_result_envelope.result_status, 'answered');
  assert.equal(result.runtime_result_envelope.selected_service_object_id, EXPLANATION_SERVICE_OBJECT_ID);
  assert.equal(result.runtime_result_envelope.answer_fragments[0].service_object.readiness_status, 'ready');
  assert.equal(dataPlatformClient.serviceCalls[0].service_object_id, EXPLANATION_SERVICE_OBJECT_ID);
});

test('operator action capabilities issue capability_access_request with operation_kind=write', async () => {
  const authKernelClient = createAuthKernelClient();
  const dataPlatformClient = createDataPlatformClient();

  const result = await runMilestoneBGuardedExecutionChain({
    runtimeRequestEnvelope: buildRuntimeRequestEnvelope({
      requested_capability_id: 'navly.ops.sync_backfill',
      requested_service_object_id: 'navly.service.ops.sync_backfill',
      access_context_envelope: buildAccessContextEnvelope({
        granted_capability_ids: ['navly.ops.sync_backfill'],
      }),
      structured_input_slots: {
        backfill_from: '2026-04-04',
        backfill_to: '2026-04-05',
        data_state_snapshot_path: '/tmp/navly-truth-store-snapshot.json',
        data_org_id: 'demo-org-001',
        data_app_secret: 'test-secret',
      },
    }),
    authKernelClient,
    dataPlatformClient,
    now: FIXED_NOW,
  });

  assert.equal(result.runtime_result_envelope.result_status, 'answered');
  assert.equal(authKernelClient.calls.length, 1);
  assert.equal(authKernelClient.calls[0].operation_kind, 'write');
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
        route_id: 'capability.navly.store.member_insight.explicit_only',
        match_mode: 'explicit_capability_id',
        match_tokens: ['会员洞察'],
        capability_id: 'navly.store.member_insight',
        default_service_object_id: 'navly.service.store.member_insight',
        supported_service_object_ids: ['navly.service.store.member_insight', EXPLANATION_SERVICE_OBJECT_ID],
        status: 'implemented_milestone_b',
      },
    ],
    default_fallback: {
      result_status: 'fallback',
      reason_code: 'runtime.route.unresolved',
      next_action: 'request_capability_clarification',
      fallback_capability_id: 'navly.system.capability_explanation',
      fallback_service_object_id: EXPLANATION_SERVICE_OBJECT_ID,
    },
  };

  const result = await runMilestoneBGuardedExecutionChain({
    runtimeRequestEnvelope: buildRuntimeRequestEnvelope({
      requested_capability_id: null,
      requested_service_object_id: null,
      user_input_text: '会员洞察',
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

test('access restricted keeps the narrowed scope and preserves restriction metadata', async () => {
  const restrictedAccessContext = buildAccessContextEnvelope({
    primary_scope_ref: 'navly:scope:store:sample-store-002',
    granted_scope_refs: ['navly:scope:store:sample-store-002'],
  });
  const authKernelClient = createAuthKernelClient({
    decisionStatus: 'restricted',
    reasonCodes: ['scope_resolution_required'],
    restrictionCodes: ['scope_limited'],
    obligationCodes: ['request_scope_confirmation'],
    effectiveAccessContext: restrictedAccessContext,
    targetScopeRef: 'navly:scope:store:sample-store-002',
  });
  const dataPlatformClient = createDataPlatformClient();

  const result = await runMilestoneBGuardedExecutionChain({
    runtimeRequestEnvelope: buildRuntimeRequestEnvelope({
      access_context_envelope: buildAccessContextEnvelope({
        granted_scope_refs: [
          'navly:scope:store:sample-store-001',
          'navly:scope:store:sample-store-002',
        ],
      }),
      target_scope_hint: 'navly:scope:store:sample-store-002',
    }),
    authKernelClient,
    dataPlatformClient,
    now: FIXED_NOW,
  });

  assert.equal(result.runtime_dependency_outcome.access_decision_status, 'restricted');
  assert.deepEqual(result.runtime_dependency_outcome.restriction_codes, ['scope_limited']);
  assert.equal(result.runtime_result_envelope.result_status, 'answered');
  assert.equal(result.runtime_dependency_outcome.readiness_query.target_scope_ref, 'navly:scope:store:sample-store-002');
  assert.equal(result.runtime_result_envelope.delivery_hints.access_decision_status, 'restricted');
});

test('readiness pending returns fallback and consumes the capability_explanation companion service', async () => {
  const authKernelClient = createAuthKernelClient();
  const dataPlatformClient = createDataPlatformClient({
    readinessStatus: 'pending',
    readinessReasonCodes: ['source_window_not_open'],
  });

  const result = await runMilestoneBGuardedExecutionChain({
    runtimeRequestEnvelope: buildRuntimeRequestEnvelope({
      requested_capability_id: 'navly.store.finance_summary',
      requested_service_object_id: capabilityServiceBinding['navly.store.finance_summary'],
    }),
    authKernelClient,
    dataPlatformClient,
    now: FIXED_NOW,
  });

  assert.equal(result.runtime_dependency_outcome.dependency_stage, 'readiness_blocked');
  assert.equal(result.runtime_result_envelope.result_status, 'fallback');
  assert.ok(result.runtime_result_envelope.reason_codes.includes('source_window_not_open'));
  assert.equal(result.runtime_dependency_outcome.explanation_service_response.service_object_id, EXPLANATION_SERVICE_OBJECT_ID);
  assert.equal(result.runtime_result_envelope.explanation_fragments[0].fragment_type, 'capability_explanation_service');
  assert.equal(dataPlatformClient.readinessCalls.length, 1);
  assert.equal(dataPlatformClient.serviceCalls.length, 1);
  assert.equal(dataPlatformClient.serviceCalls[0].service_object_id, EXPLANATION_SERVICE_OBJECT_ID);
  assert.equal(result.runtime_dependency_outcome.explanation_service_query.target_business_date, '2026-04-06');
  assert.equal(dataPlatformClient.serviceCalls[0].target_business_date, '2026-04-06');
});

test('readiness failed returns fallback with explanation_object companion output', async () => {
  const authKernelClient = createAuthKernelClient();
  const dataPlatformClient = createDataPlatformClient({
    readinessStatus: 'failed',
    readinessReasonCodes: ['upstream_error'],
  });

  const result = await runMilestoneBGuardedExecutionChain({
    runtimeRequestEnvelope: buildRuntimeRequestEnvelope({
      requested_capability_id: 'navly.store.finance_summary',
      requested_service_object_id: capabilityServiceBinding['navly.store.finance_summary'],
    }),
    authKernelClient,
    dataPlatformClient,
    now: FIXED_NOW,
  });

  assert.equal(result.runtime_dependency_outcome.readiness_response.readiness_status, 'failed');
  assert.equal(result.runtime_result_envelope.result_status, 'fallback');
  assert.equal(result.runtime_result_envelope.explanation_fragments[0].explanation_object.reason_codes[0], 'upstream_error');
});

test('readiness unsupported_scope still produces a structured explanation fragment', async () => {
  const authKernelClient = createAuthKernelClient();
  const dataPlatformClient = createDataPlatformClient({
    readinessStatus: 'unsupported_scope',
    readinessReasonCodes: ['capability_scope_not_supported'],
  });

  const result = await runMilestoneBGuardedExecutionChain({
    runtimeRequestEnvelope: buildRuntimeRequestEnvelope({
      requested_capability_id: 'navly.store.staff_board',
      requested_service_object_id: capabilityServiceBinding['navly.store.staff_board'],
    }),
    authKernelClient,
    dataPlatformClient,
    now: FIXED_NOW,
  });

  assert.equal(result.runtime_dependency_outcome.readiness_response.readiness_status, 'unsupported_scope');
  assert.equal(result.runtime_result_envelope.result_status, 'fallback');
  assert.equal(result.runtime_result_envelope.explanation_fragments[0].fragment_type, 'capability_explanation_service');
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
  assert.equal(result.runtime_result_envelope.explanation_fragments[0].fragment_type, 'capability_explanation_object');
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
