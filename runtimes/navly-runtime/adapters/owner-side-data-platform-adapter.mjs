import path from 'node:path';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import { fileURLToPath } from 'node:url';

const execFileAsync = promisify(execFile);
const moduleDir = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(moduleDir, '..', '..', '..');
const defaultDataPlatformRoot = path.join(repoRoot, 'platforms', 'data-platform');
const defaultFixtureBundlePath = path.join(
  defaultDataPlatformRoot,
  'tests',
  'fixtures',
  'member_insight',
  'qinqin_fixture_pages.bundle.json',
);

const capabilityBindings = Object.freeze({
  'navly.store.member_insight': {
    serviceObjectId: 'navly.service.store.member_insight',
    mode: 'member_insight',
  },
  'navly.store.daily_overview': {
    serviceObjectId: 'navly.service.store.daily_overview',
    mode: 'daily_overview',
  },
  'navly.store.finance_summary': {
    serviceObjectId: 'navly.service.store.finance_summary',
    mode: 'pending_manager_surface',
    pendingReasonCode: 'owner_surface_pending',
  },
  'navly.store.staff_board': {
    serviceObjectId: 'navly.service.store.staff_board',
    mode: 'pending_manager_surface',
    pendingReasonCode: 'owner_surface_pending',
  },
  'navly.system.capability_explanation': {
    serviceObjectId: 'navly.service.system.capability_explanation',
    mode: 'capability_explanation',
  },
  'navly.ops.sync_status': {
    serviceObjectId: 'navly.service.ops.sync_status',
    mode: 'pending_operator_surface',
    pendingReasonCode: 'operator_surface_pending',
  },
  'navly.ops.backfill_status': {
    serviceObjectId: 'navly.service.ops.backfill_status',
    mode: 'pending_operator_surface',
    pendingReasonCode: 'operator_surface_pending',
  },
  'navly.ops.sync_rerun': {
    serviceObjectId: 'navly.service.ops.sync_rerun',
    mode: 'pending_operator_surface',
    pendingReasonCode: 'operator_surface_pending',
  },
  'navly.ops.sync_backfill': {
    serviceObjectId: 'navly.service.ops.sync_backfill',
    mode: 'pending_operator_surface',
    pendingReasonCode: 'operator_surface_pending',
  },
  'navly.ops.quality_report': {
    serviceObjectId: 'navly.service.ops.quality_report',
    mode: 'pending_operator_surface',
    pendingReasonCode: 'operator_surface_pending',
  },
});

const memberInsightOwnerSurfaceCode = String.raw`import json
import sys
from pathlib import Path

data_platform_root = Path(sys.argv[1]).resolve()
if str(data_platform_root) not in sys.path:
    sys.path.insert(0, str(data_platform_root))

from connectors.qinqin.qinqin_substrate import (
    DEFAULT_LIVE_TIMEOUT_MS,
    FixtureQinqinTransport,
    LiveQinqinTransport,
)
from workflows.member_insight_owner_surface import build_member_insight_owner_surface

args = json.loads(sys.argv[2])
transport_kind = args.get("transport_kind") or "fixture"
if transport_kind == "fixture":
    fixture_bundle = json.loads(Path(args["fixture_bundle_path"]).read_text(encoding="utf-8"))
    transport = FixtureQinqinTransport(fixture_bundle)
else:
    live_timeout_ms = args.get("live_timeout_ms") or DEFAULT_LIVE_TIMEOUT_MS
    transport = LiveQinqinTransport(
        base_url=args["live_base_url"],
        timeout_ms=int(live_timeout_ms),
        authorization=args.get("live_authorization"),
        token=args.get("live_token"),
    )

result = build_member_insight_owner_surface(
    request_id=args["request_id"],
    trace_ref=args["trace_ref"],
    target_scope_ref=args["target_scope_ref"],
    target_business_date=args["requested_business_date"],
    org_id=args["org_id"],
    start_time=args["start_time"],
    end_time=args["end_time"],
    app_secret=args["app_secret"],
    transport=transport,
)
print(json.dumps({
    "readiness_response": result["readiness_response"],
    "theme_service_response": result["theme_service_response"],
}, ensure_ascii=False))`;

function asNonEmptyString(value) {
  return typeof value === 'string' && value.trim().length > 0 ? value.trim() : null;
}

function sanitizeRefSegment(value) {
  const normalized = String(value ?? '')
    .trim()
    .replace(/[^A-Za-z0-9._:-]+/g, '-')
    .replace(/^-+|-+$/g, '');
  return normalized || 'unknown';
}

function nowIso() {
  return new Date().toISOString();
}

function buildSyntheticStateTraceRefs(kind, capabilityId, targetScopeRef, businessDate) {
  return [
    `navly:state-trace:${sanitizeRefSegment(kind)}:${sanitizeRefSegment(capabilityId)}:${sanitizeRefSegment(targetScopeRef)}:${sanitizeRefSegment(businessDate)}`,
  ];
}

function buildSyntheticRunTraceRefs(kind, capabilityId, businessDate) {
  return [
    `navly:run-trace:${sanitizeRefSegment(kind)}:${sanitizeRefSegment(capabilityId)}:${sanitizeRefSegment(businessDate)}`,
  ];
}

function buildExplanationObject({
  capabilityId,
  reasonCodes,
  stateTraceRefs,
  runTraceRefs,
  summaryTokens = [],
  extensions = {},
}) {
  return {
    capability_id: capabilityId,
    explanation_scope: 'service',
    reason_codes: [...reasonCodes],
    summary_tokens: [...summaryTokens],
    state_trace_refs: [...stateTraceRefs],
    run_trace_refs: [...runTraceRefs],
    extensions: { ...extensions },
  };
}

function buildReadinessResponse({
  query,
  capabilityId,
  readinessStatus,
  latestUsableBusinessDate,
  reasonCodes,
  stateTraceRefs,
  runTraceRefs,
  blockingDependencies = [],
  extensions = {},
}) {
  return {
    request_id: query.request_id,
    trace_ref: query.trace_ref,
    capability_id: capabilityId,
    readiness_status: readinessStatus,
    evaluated_scope_ref: query.target_scope_ref,
    requested_business_date: query.target_business_date,
    latest_usable_business_date: latestUsableBusinessDate,
    reason_codes: [...reasonCodes],
    blocking_dependencies: [...blockingDependencies],
    state_trace_refs: [...stateTraceRefs],
    run_trace_refs: [...runTraceRefs],
    evaluated_at: nowIso(),
    extensions: { ...extensions },
  };
}

function buildThemeServiceResponse({
  query,
  capabilityId,
  serviceObjectId,
  serviceStatus,
  serviceObject,
  latestUsableBusinessDate,
  stateTraceRefs,
  runTraceRefs,
  explanationObject = undefined,
  extensions = {},
}) {
  return {
    request_id: query.request_id,
    trace_ref: query.trace_ref,
    capability_id: capabilityId,
    service_object_id: serviceObjectId,
    service_status: serviceStatus,
    service_object: serviceObject,
    data_window: {
      from: latestUsableBusinessDate,
      to: latestUsableBusinessDate,
    },
    explanation_object: explanationObject,
    state_trace_refs: [...stateTraceRefs],
    run_trace_refs: [...runTraceRefs],
    served_at: nowIso(),
    extensions: { ...extensions },
  };
}

function buildUnsupportedReadiness(query) {
  return {
    request_id: query.request_id,
    trace_ref: query.trace_ref,
    capability_id: query.capability_id,
    readiness_status: 'unsupported_scope',
    evaluated_scope_ref: query.target_scope_ref,
    requested_business_date: query.target_business_date,
    latest_usable_business_date: query.target_business_date,
    reason_codes: ['capability_not_registered'],
    blocking_dependencies: [],
    state_trace_refs: [],
    run_trace_refs: [],
    evaluated_at: nowIso(),
  };
}

function buildScopeMismatchService(query, capabilityId, serviceObjectId, reasonCodes = ['service_binding_mismatch']) {
  const stateTraceRefs = buildSyntheticStateTraceRefs('scope-mismatch', capabilityId, query.target_scope_ref, query.target_business_date);
  const runTraceRefs = buildSyntheticRunTraceRefs('scope-mismatch', capabilityId, query.target_business_date);

  return buildThemeServiceResponse({
    query,
    capabilityId,
    serviceObjectId,
    serviceStatus: 'scope_mismatch',
    serviceObject: {},
    latestUsableBusinessDate: query.target_business_date,
    stateTraceRefs,
    runTraceRefs,
    explanationObject: buildExplanationObject({
      capabilityId,
      reasonCodes,
      stateTraceRefs,
      runTraceRefs,
      summaryTokens: [capabilityId, 'scope_mismatch', serviceObjectId],
      extensions: {
        owner_surface: 'host_publication_closeout',
      },
    }),
    extensions: {
      owner_surface: 'host_publication_closeout',
    },
  });
}

function buildPendingCapabilityReadiness(query, capabilityId, reasonCode, ownerSurface = null) {
  const latestUsableBusinessDate = ownerSurface?.readiness_response?.latest_usable_business_date ?? query.target_business_date;
  const stateTraceRefs = ownerSurface?.readiness_response?.state_trace_refs
    ?? buildSyntheticStateTraceRefs('pending-capability', capabilityId, query.target_scope_ref, latestUsableBusinessDate);
  const runTraceRefs = ownerSurface?.readiness_response?.run_trace_refs
    ?? buildSyntheticRunTraceRefs('pending-capability', capabilityId, latestUsableBusinessDate);

  return buildReadinessResponse({
    query,
    capabilityId,
    readinessStatus: 'pending',
    latestUsableBusinessDate,
    reasonCodes: [reasonCode],
    stateTraceRefs,
    runTraceRefs,
    extensions: {
      owner_surface: 'host_publication_closeout',
    },
  });
}

function buildPendingCapabilityService(query, capabilityId, serviceObjectId, reasonCode, ownerSurface = null) {
  const latestUsableBusinessDate = ownerSurface?.readiness_response?.latest_usable_business_date ?? query.target_business_date;
  const stateTraceRefs = ownerSurface?.readiness_response?.state_trace_refs
    ?? buildSyntheticStateTraceRefs('pending-capability', capabilityId, query.target_scope_ref, latestUsableBusinessDate);
  const runTraceRefs = ownerSurface?.readiness_response?.run_trace_refs
    ?? buildSyntheticRunTraceRefs('pending-capability', capabilityId, latestUsableBusinessDate);

  return buildThemeServiceResponse({
    query,
    capabilityId,
    serviceObjectId,
    serviceStatus: 'not_ready',
    serviceObject: {},
    latestUsableBusinessDate,
    stateTraceRefs,
    runTraceRefs,
    explanationObject: buildExplanationObject({
      capabilityId,
      reasonCodes: [reasonCode],
      stateTraceRefs,
      runTraceRefs,
      summaryTokens: [capabilityId, 'pending', latestUsableBusinessDate],
      extensions: {
        owner_surface: 'host_publication_closeout',
      },
    }),
    extensions: {
      owner_surface: 'host_publication_closeout',
    },
  });
}

function extractMemberInsightEvidence(ownerSurface, fallbackBusinessDate) {
  const readinessResponse = ownerSurface?.readiness_response ?? null;
  return {
    latestUsableBusinessDate: readinessResponse?.latest_usable_business_date ?? fallbackBusinessDate,
    stateTraceRefs: [...(readinessResponse?.state_trace_refs ?? [])],
    runTraceRefs: [...(readinessResponse?.run_trace_refs ?? [])],
    readinessStatus: readinessResponse?.readiness_status ?? 'pending',
    reasonCodes: [...(readinessResponse?.reason_codes ?? ['dependency_context_unavailable'])],
  };
}

function buildDailyOverviewServiceObject(query, ownerSurface) {
  const memberServiceObject = ownerSurface?.theme_service_response?.service_object ?? {};
  const latestUsableBusinessDate = ownerSurface?.readiness_response?.latest_usable_business_date ?? query.target_business_date;

  return {
    capability_id: 'navly.store.daily_overview',
    service_object_id: 'navly.service.store.daily_overview',
    target_scope_ref: query.target_scope_ref,
    target_business_date: query.target_business_date,
    latest_usable_business_date: latestUsableBusinessDate,
    overview_summary: {
      customer_count: memberServiceObject.customer_count ?? 0,
      customer_card_count: memberServiceObject.customer_card_count ?? 0,
      consume_bill_count: memberServiceObject.consume_bill_count ?? 0,
      consume_bill_payment_count: memberServiceObject.consume_bill_payment_count ?? 0,
    },
    key_metrics: [
      { metric_id: 'customer_count', value: memberServiceObject.customer_count ?? 0 },
      { metric_id: 'customer_card_count', value: memberServiceObject.customer_card_count ?? 0 },
      { metric_id: 'consume_bill_count', value: memberServiceObject.consume_bill_count ?? 0 },
      { metric_id: 'consume_bill_payment_count', value: memberServiceObject.consume_bill_payment_count ?? 0 },
    ],
    risk_flags: [
      {
        risk_id: 'finance_summary_pending',
        severity: 'info',
        reason_code: 'owner_surface_pending',
      },
      {
        risk_id: 'staff_board_pending',
        severity: 'info',
        reason_code: 'owner_surface_pending',
      },
    ],
    capability_readiness: {
      member_insight: ownerSurface?.readiness_response?.readiness_status ?? 'pending',
      finance_summary: 'pending',
      staff_board: 'pending',
    },
  };
}

function buildCapabilityExplanationServiceObject(query) {
  const requestedFreshnessMode = asNonEmptyString(query?.extensions?.requested_freshness_mode)
    ?? asNonEmptyString(query?.extensions?.freshness_mode)
    ?? 'latest_usable';

  return {
    capability_id: 'navly.system.capability_explanation',
    service_object_id: 'navly.service.system.capability_explanation',
    target_scope_ref: query.target_scope_ref,
    target_business_date: query.target_business_date,
    explanation_status: 'structured',
    requested_freshness_mode: requestedFreshnessMode,
    explanation_target_capability_id: asNonEmptyString(query?.extensions?.explanation_target_capability_id),
    explanation_target_service_object_id: asNonEmptyString(query?.extensions?.explanation_target_service_object_id),
    guidance_tokens: [
      'use_first_party_tool_surface',
      'respect_access_context_envelope',
      'review_capability_reason_codes',
    ],
  };
}

function resolveDataContext(query, adapterOptions) {
  const contextFromQuery = query?.extensions?.data_adapter_context ?? {};
  const targetBusinessDate = asNonEmptyString(query?.target_business_date);
  if (!targetBusinessDate) {
    throw new Error('owner-side data adapter requires target_business_date');
  }

  const orgId = asNonEmptyString(contextFromQuery.org_id) ?? asNonEmptyString(adapterOptions.defaultOrgId);
  if (!orgId) {
    throw new Error('owner-side data adapter requires org_id');
  }

  const appSecret = asNonEmptyString(contextFromQuery.app_secret)
    ?? asNonEmptyString(adapterOptions.defaultAppSecret)
    ?? asNonEmptyString(process.env.NAVLY_RUNTIME_DATA_APP_SECRET);
  if (!appSecret) {
    throw new Error('owner-side data adapter requires app_secret');
  }

  const fixtureBundlePath = asNonEmptyString(contextFromQuery.fixture_bundle_path)
    ?? asNonEmptyString(adapterOptions.fixtureBundlePath)
    ?? defaultFixtureBundlePath;
  const transportKind = asNonEmptyString(contextFromQuery.transport_kind) ?? 'fixture';

  const startTime = asNonEmptyString(contextFromQuery.start_time) ?? `${targetBusinessDate} 00:00:00`;
  const endTime = asNonEmptyString(contextFromQuery.end_time) ?? `${targetBusinessDate} 23:59:59`;
  const liveBaseUrl = asNonEmptyString(contextFromQuery.live_base_url)
    ?? asNonEmptyString(adapterOptions.liveBaseUrl)
    ?? asNonEmptyString(process.env.QINQIN_API_BASE_URL)
    ?? asNonEmptyString(process.env.QINQIN_REAL_DATA_URL);
  const liveAuthorization = asNonEmptyString(contextFromQuery.live_authorization)
    ?? asNonEmptyString(adapterOptions.liveAuthorization)
    ?? asNonEmptyString(process.env.QINQIN_API_AUTHORIZATION);
  const liveToken = asNonEmptyString(contextFromQuery.live_token)
    ?? asNonEmptyString(adapterOptions.liveToken)
    ?? asNonEmptyString(process.env.QINQIN_API_TOKEN)
    ?? asNonEmptyString(process.env.QINQIN_REAL_DATA_TOKEN);
  const liveTimeoutMs = Number(
    contextFromQuery.live_timeout_ms
      ?? adapterOptions.liveTimeoutMs
      ?? process.env.QINQIN_API_REQUEST_TIMEOUT_MS
      ?? 15000,
  );

  return {
    request_id: query.request_id,
    trace_ref: query.trace_ref,
    target_scope_ref: query.target_scope_ref,
    org_id: orgId,
    requested_business_date: targetBusinessDate,
    start_time: startTime,
    end_time: endTime,
    app_secret: appSecret,
    fixture_bundle_path: fixtureBundlePath,
    transport_kind: transportKind,
    live_base_url: liveBaseUrl,
    live_authorization: liveAuthorization,
    live_token: liveToken,
    live_timeout_ms: (Number.isFinite(liveTimeoutMs) && liveTimeoutMs > 0) ? liveTimeoutMs : 15000,
  };
}

async function runMemberInsightOwnerSurface({
  pythonExecutable,
  dataPlatformRoot,
  input,
}) {
  const pythonPath = [dataPlatformRoot, process.env.PYTHONPATH].filter(Boolean).join(path.delimiter);
  const { stdout, stderr } = await execFileAsync(
    pythonExecutable,
    [
      '-c',
      memberInsightOwnerSurfaceCode,
      dataPlatformRoot,
      JSON.stringify(input),
    ],
    {
      maxBuffer: 8 * 1024 * 1024,
      env: {
        ...process.env,
        PYTHONPATH: pythonPath,
      },
    },
  );

  const payloadText = String(stdout ?? '').trim();
  if (!payloadText) {
    throw new Error(`owner-side data adapter returned empty payload: ${String(stderr ?? '').trim()}`);
  }

  return JSON.parse(payloadText);
}

function pruneExpiredRunCache(runCache, nowEpochMs, runCacheTtlMs) {
  if (!Number.isFinite(runCacheTtlMs) || runCacheTtlMs <= 0) {
    return;
  }

  for (const [cacheKey, cacheEntry] of runCache.entries()) {
    if ((nowEpochMs - cacheEntry.created_at_epoch_ms) > runCacheTtlMs) {
      runCache.delete(cacheKey);
    }
  }
}

function enforceRunCacheBound(runCache, runCacheMaxEntries) {
  if (!Number.isFinite(runCacheMaxEntries) || runCacheMaxEntries <= 0) {
    runCache.clear();
    return;
  }

  while (runCache.size > runCacheMaxEntries) {
    const oldestCacheKey = runCache.keys().next().value;
    if (oldestCacheKey === undefined) {
      break;
    }
    runCache.delete(oldestCacheKey);
  }
}

export function createOwnerSideDataPlatformAdapter({
  pythonExecutable = 'python3',
  dataPlatformRoot = defaultDataPlatformRoot,
  defaultOrgId = null,
  defaultAppSecret = null,
  fixtureBundlePath = defaultFixtureBundlePath,
  liveBaseUrl = null,
  liveAuthorization = null,
  liveToken = null,
  liveTimeoutMs = 15000,
  runCacheMaxEntries = 32,
  runCacheTtlMs = 5 * 60 * 1000,
  nowEpochMsFactory = () => Date.now(),
  runMemberInsightOwnerSurfaceImpl = runMemberInsightOwnerSurface,
} = {}) {
  const runCache = new Map();

  async function loadMemberInsightOwnerSurface(query) {
    const context = resolveDataContext(query, {
      defaultOrgId,
      defaultAppSecret,
      fixtureBundlePath,
      liveBaseUrl,
      liveAuthorization,
      liveToken,
      liveTimeoutMs,
    });

    const cacheKey = JSON.stringify([
      query.request_id,
      query.trace_ref,
      query.target_scope_ref,
      context.org_id,
      context.requested_business_date,
      context.start_time,
      context.end_time,
      context.fixture_bundle_path,
      context.transport_kind,
      context.live_base_url,
      context.live_authorization,
      context.live_token,
      context.live_timeout_ms,
    ]);

    const nowEpochMsCandidate = Number(nowEpochMsFactory());
    const nowEpochMs = Number.isFinite(nowEpochMsCandidate) ? nowEpochMsCandidate : Date.now();
    pruneExpiredRunCache(runCache, nowEpochMs, runCacheTtlMs);

    const cachedEntry = runCache.get(cacheKey);
    if (cachedEntry?.promise) {
      return cachedEntry.promise;
    }

    const runPromise = runMemberInsightOwnerSurfaceImpl({
      pythonExecutable,
      dataPlatformRoot,
      input: context,
    }).catch((error) => {
      runCache.delete(cacheKey);
      throw error;
    });

    runCache.set(cacheKey, {
      promise: runPromise,
      created_at_epoch_ms: nowEpochMs,
    });
    enforceRunCacheBound(runCache, runCacheMaxEntries);

    return runPromise;
  }

  async function safeLoadMemberInsightOwnerSurface(query) {
    try {
      return await loadMemberInsightOwnerSurface({
        ...query,
        capability_id: 'navly.store.member_insight',
      });
    } catch (error) {
      return {
        error,
      };
    }
  }

  return {
    async queryCapabilityReadiness(query) {
      const capabilityConfig = capabilityBindings[query.capability_id];
      if (!capabilityConfig) {
        return buildUnsupportedReadiness(query);
      }

      if (capabilityConfig.mode === 'member_insight') {
        const ownerSurface = await loadMemberInsightOwnerSurface(query);
        return ownerSurface.readiness_response;
      }

      if (capabilityConfig.mode === 'daily_overview') {
        const ownerSurface = await safeLoadMemberInsightOwnerSurface(query);
        if (ownerSurface?.error) {
          return buildPendingCapabilityReadiness(query, query.capability_id, 'dependency_context_unavailable');
        }

        const memberEvidence = extractMemberInsightEvidence(ownerSurface, query.target_business_date);
        if (memberEvidence.readinessStatus !== 'ready') {
          return buildReadinessResponse({
            query,
            capabilityId: query.capability_id,
            readinessStatus: memberEvidence.readinessStatus,
            latestUsableBusinessDate: memberEvidence.latestUsableBusinessDate,
            reasonCodes: memberEvidence.reasonCodes,
            stateTraceRefs: memberEvidence.stateTraceRefs,
            runTraceRefs: memberEvidence.runTraceRefs,
            blockingDependencies: [...(ownerSurface.readiness_response?.blocking_dependencies ?? [])],
            extensions: {
              owner_surface: 'daily_overview',
              derived_from_capability_id: 'navly.store.member_insight',
            },
          });
        }

        return buildReadinessResponse({
          query,
          capabilityId: query.capability_id,
          readinessStatus: 'ready',
          latestUsableBusinessDate: memberEvidence.latestUsableBusinessDate,
          reasonCodes: [],
          stateTraceRefs: memberEvidence.stateTraceRefs,
          runTraceRefs: memberEvidence.runTraceRefs,
          extensions: {
            owner_surface: 'daily_overview',
            derived_from_capability_id: 'navly.store.member_insight',
          },
        });
      }

      if (capabilityConfig.mode === 'capability_explanation') {
        const stateTraceRefs = buildSyntheticStateTraceRefs('capability-explanation', query.capability_id, query.target_scope_ref, query.target_business_date);
        const runTraceRefs = buildSyntheticRunTraceRefs('capability-explanation', query.capability_id, query.target_business_date);
        return buildReadinessResponse({
          query,
          capabilityId: query.capability_id,
          readinessStatus: 'ready',
          latestUsableBusinessDate: query.target_business_date,
          reasonCodes: [],
          stateTraceRefs,
          runTraceRefs,
          extensions: {
            owner_surface: 'capability_explanation',
          },
        });
      }

      const ownerSurface = capabilityConfig.mode === 'pending_manager_surface'
        ? await safeLoadMemberInsightOwnerSurface(query)
        : null;

      return buildPendingCapabilityReadiness(
        query,
        query.capability_id,
        capabilityConfig.pendingReasonCode,
        ownerSurface?.error ? null : ownerSurface,
      );
    },

    async queryThemeService(query) {
      const capabilityConfig = capabilityBindings[query.capability_id];
      if (!capabilityConfig) {
        return buildScopeMismatchService(
          query,
          query.capability_id,
          query.service_object_id,
          ['capability_not_registered'],
        );
      }

      if (query.service_object_id !== capabilityConfig.serviceObjectId) {
        return buildScopeMismatchService(query, query.capability_id, query.service_object_id);
      }

      if (capabilityConfig.mode === 'member_insight') {
        const ownerSurface = await loadMemberInsightOwnerSurface(query);
        return ownerSurface.theme_service_response;
      }

      if (capabilityConfig.mode === 'daily_overview') {
        const ownerSurface = await safeLoadMemberInsightOwnerSurface(query);
        if (ownerSurface?.error) {
          return buildPendingCapabilityService(
            query,
            query.capability_id,
            capabilityConfig.serviceObjectId,
            'dependency_context_unavailable',
          );
        }

        const memberEvidence = extractMemberInsightEvidence(ownerSurface, query.target_business_date);
        if (memberEvidence.readinessStatus !== 'ready') {
          return buildThemeServiceResponse({
            query,
            capabilityId: query.capability_id,
            serviceObjectId: capabilityConfig.serviceObjectId,
            serviceStatus: 'not_ready',
            serviceObject: {},
            latestUsableBusinessDate: memberEvidence.latestUsableBusinessDate,
            stateTraceRefs: memberEvidence.stateTraceRefs,
            runTraceRefs: memberEvidence.runTraceRefs,
            explanationObject: buildExplanationObject({
              capabilityId: query.capability_id,
              reasonCodes: memberEvidence.reasonCodes,
              stateTraceRefs: memberEvidence.stateTraceRefs,
              runTraceRefs: memberEvidence.runTraceRefs,
              summaryTokens: [query.capability_id, 'not_ready', memberEvidence.latestUsableBusinessDate],
              extensions: {
                owner_surface: 'daily_overview',
                derived_from_capability_id: 'navly.store.member_insight',
              },
            }),
            extensions: {
              owner_surface: 'daily_overview',
              derived_from_capability_id: 'navly.store.member_insight',
              readiness_status: memberEvidence.readinessStatus,
            },
          });
        }

        return buildThemeServiceResponse({
          query,
          capabilityId: query.capability_id,
          serviceObjectId: capabilityConfig.serviceObjectId,
          serviceStatus: 'served',
          serviceObject: buildDailyOverviewServiceObject(query, ownerSurface),
          latestUsableBusinessDate: memberEvidence.latestUsableBusinessDate,
          stateTraceRefs: memberEvidence.stateTraceRefs,
          runTraceRefs: memberEvidence.runTraceRefs,
          extensions: {
            owner_surface: 'daily_overview',
            derived_from_capability_id: 'navly.store.member_insight',
          },
        });
      }

      if (capabilityConfig.mode === 'capability_explanation') {
        const stateTraceRefs = buildSyntheticStateTraceRefs('capability-explanation', query.capability_id, query.target_scope_ref, query.target_business_date);
        const runTraceRefs = buildSyntheticRunTraceRefs('capability-explanation', query.capability_id, query.target_business_date);
        return buildThemeServiceResponse({
          query,
          capabilityId: query.capability_id,
          serviceObjectId: capabilityConfig.serviceObjectId,
          serviceStatus: 'served',
          serviceObject: buildCapabilityExplanationServiceObject(query),
          latestUsableBusinessDate: query.target_business_date,
          stateTraceRefs,
          runTraceRefs,
          extensions: {
            owner_surface: 'capability_explanation',
          },
        });
      }

      const ownerSurface = capabilityConfig.mode === 'pending_manager_surface'
        ? await safeLoadMemberInsightOwnerSurface(query)
        : null;

      return buildPendingCapabilityService(
        query,
        query.capability_id,
        capabilityConfig.serviceObjectId,
        capabilityConfig.pendingReasonCode,
        ownerSurface?.error ? null : ownerSurface,
      );
    },
  };
}
