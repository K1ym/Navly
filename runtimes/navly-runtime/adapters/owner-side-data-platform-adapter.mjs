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

const EXPLANATION_SERVICE_OBJECT_ID = 'navly.service.system.capability_explanation';

const publishedCapabilitySurfaceCatalog = {
  'navly.store.member_insight': {
    defaultServiceObjectId: 'navly.service.store.member_insight',
    fixtureBundlePaths: [
      path.join(defaultDataPlatformRoot, 'tests', 'fixtures', 'member_insight', 'qinqin_fixture_pages.bundle.json'),
    ],
  },
  'navly.store.staff_board': {
    defaultServiceObjectId: 'navly.service.store.staff_board',
    fixtureBundlePaths: [
      path.join(defaultDataPlatformRoot, 'tests', 'fixtures', 'staff_board', 'qinqin_staff_fixture_pages.bundle.json'),
    ],
  },
  'navly.store.finance_summary': {
    defaultServiceObjectId: 'navly.service.store.finance_summary',
    fixtureBundlePaths: [
      path.join(defaultDataPlatformRoot, 'tests', 'fixtures', 'finance_summary', 'qinqin_fixture_pages.bundle.json'),
    ],
  },
  'navly.store.daily_overview': {
    defaultServiceObjectId: 'navly.service.store.daily_overview',
    fixtureBundlePaths: [
      path.join(defaultDataPlatformRoot, 'tests', 'fixtures', 'member_insight', 'qinqin_fixture_pages.bundle.json'),
      path.join(defaultDataPlatformRoot, 'tests', 'fixtures', 'staff_board', 'qinqin_staff_fixture_pages.bundle.json'),
      path.join(defaultDataPlatformRoot, 'tests', 'fixtures', 'finance_summary', 'qinqin_fixture_pages.bundle.json'),
    ],
  },
};

const ownerSurfaceCode = String.raw`import json
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
from workflows.capability_explanation_owner_surface import build_capability_explanation_owner_surface
from workflows.daily_overview_owner_surface import build_daily_overview_owner_surface
from workflows.finance_summary_owner_surface import build_finance_summary_owner_surface
from workflows.member_insight_owner_surface import build_member_insight_owner_surface
from workflows.staff_board_owner_surface import build_staff_board_owner_surface

EXPLANATION_SERVICE_OBJECT_ID = "navly.service.system.capability_explanation"

args = json.loads(sys.argv[2])
transport_kind = args.get("transport_kind") or "fixture"
if transport_kind == "fixture":
    fixture_bundle = {}
    bundle_paths = args.get("fixture_bundle_paths") or []
    if not bundle_paths and args.get("fixture_bundle_path"):
        bundle_paths = [args["fixture_bundle_path"]]
    for bundle_path in bundle_paths:
        fixture_bundle.update(json.loads(Path(bundle_path).read_text(encoding="utf-8")))
    transport = FixtureQinqinTransport(fixture_bundle)
else:
    live_timeout_ms = args.get("live_timeout_ms") or DEFAULT_LIVE_TIMEOUT_MS
    transport = LiveQinqinTransport(
        base_url=args["live_base_url"],
        timeout_ms=int(live_timeout_ms),
        authorization=args.get("live_authorization"),
        token=args.get("live_token"),
    )

base_kwargs = {
    "request_id": args["request_id"],
    "trace_ref": args["trace_ref"],
    "target_scope_ref": args["target_scope_ref"],
    "target_business_date": args["requested_business_date"],
    "org_id": args["org_id"],
    "start_time": args["start_time"],
    "end_time": args["end_time"],
    "app_secret": args["app_secret"],
    "transport": transport,
}

requested_capability_id = args["requested_capability_id"]
requested_service_object_id = args.get("requested_service_object_id")

if requested_service_object_id == EXPLANATION_SERVICE_OBJECT_ID:
    result = build_capability_explanation_owner_surface(
        requested_capability_id=requested_capability_id,
        requested_service_object_id=requested_service_object_id,
        **base_kwargs,
    )
    readiness_response = result["readiness_response"]
    theme_service_response = result.get("theme_service_response")
    service_response = result["explanation_service_response"]
else:
    if requested_capability_id == "navly.store.member_insight":
        result = build_member_insight_owner_surface(**base_kwargs)
    elif requested_capability_id == "navly.store.staff_board":
        result = build_staff_board_owner_surface(**base_kwargs)
    elif requested_capability_id == "navly.store.finance_summary":
        result = build_finance_summary_owner_surface(**base_kwargs)
    elif requested_capability_id == "navly.store.daily_overview":
        result = build_daily_overview_owner_surface(**base_kwargs)
    else:
        raise KeyError(f"unsupported owner surface capability: {requested_capability_id}")

    readiness_response = result["readiness_response"]
    theme_service_response = result["theme_service_response"]
    service_response = result["theme_service_response"]

print(json.dumps({
    "readiness_response": readiness_response,
    "theme_service_response": theme_service_response,
    "service_response": service_response,
}, ensure_ascii=False))`;

function asNonEmptyString(value) {
  return typeof value === 'string' && value.trim().length > 0 ? value.trim() : null;
}

function asNonEmptyStringArray(value) {
  if (!Array.isArray(value)) {
    return [];
  }

  return value
    .filter((entry) => typeof entry === 'string' && entry.trim().length > 0)
    .map((entry) => entry.trim());
}

function resolveFixtureBundlePaths(capabilityId, contextFromQuery, adapterOptions) {
  const explicitContextPaths = asNonEmptyStringArray(contextFromQuery.fixture_bundle_paths);
  if (explicitContextPaths.length > 0) {
    return explicitContextPaths;
  }

  const explicitOptionPaths = asNonEmptyStringArray(adapterOptions.fixtureBundlePaths);
  if (explicitOptionPaths.length > 0) {
    return explicitOptionPaths;
  }

  const explicitSinglePath = asNonEmptyString(contextFromQuery.fixture_bundle_path)
    ?? asNonEmptyString(adapterOptions.fixtureBundlePath);
  if (explicitSinglePath) {
    return [explicitSinglePath];
  }

  return [...(publishedCapabilitySurfaceCatalog[capabilityId]?.fixtureBundlePaths ?? [defaultFixtureBundlePath])];
}

function resolveDataContext(query, adapterOptions) {
  const contextFromQuery = query?.extensions?.data_adapter_context ?? {};
  const requestedCapabilityId = asNonEmptyString(query?.capability_id);
  const requestedServiceObjectId = asNonEmptyString(query?.service_object_id);
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
  const transportKind = asNonEmptyString(contextFromQuery.transport_kind) ?? 'fixture';

  return {
    request_id: query.request_id,
    trace_ref: query.trace_ref,
    target_scope_ref: query.target_scope_ref,
    requested_capability_id: requestedCapabilityId,
    requested_service_object_id: requestedServiceObjectId,
    org_id: orgId,
    requested_business_date: targetBusinessDate,
    start_time: startTime,
    end_time: endTime,
    app_secret: appSecret,
    fixture_bundle_paths: resolveFixtureBundlePaths(requestedCapabilityId, contextFromQuery, adapterOptions),
    transport_kind: transportKind,
    live_base_url: liveBaseUrl,
    live_authorization: liveAuthorization,
    live_token: liveToken,
    live_timeout_ms: (Number.isFinite(liveTimeoutMs) && liveTimeoutMs > 0) ? liveTimeoutMs : 15000,
  };
}

async function runPublishedOwnerSurface({
  pythonExecutable,
  dataPlatformRoot,
  input,
}) {
  const pythonPath = [dataPlatformRoot, process.env.PYTHONPATH].filter(Boolean).join(path.delimiter);
  const { stdout, stderr } = await execFileAsync(
    pythonExecutable,
    [
      '-c',
      ownerSurfaceCode,
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

function buildUnsupportedReadiness(query, reasonCodes = ['capability_scope_not_supported']) {
  return {
    request_id: query.request_id,
    trace_ref: query.trace_ref,
    capability_id: query.capability_id,
    readiness_status: 'unsupported_scope',
    evaluated_scope_ref: query.target_scope_ref,
    requested_business_date: query.target_business_date,
    latest_usable_business_date: query.target_business_date,
    reason_codes: reasonCodes,
    blocking_dependencies: [],
    state_trace_refs: [],
    run_trace_refs: [],
    evaluated_at: new Date().toISOString(),
  };
}

function buildScopeMismatchService(query, reasonCodes = ['projection_not_available']) {
  return {
    request_id: query.request_id,
    trace_ref: query.trace_ref,
    capability_id: query.capability_id,
    service_object_id: query.service_object_id,
    service_status: 'scope_mismatch',
    service_object: {},
    data_window: {
      from: query.target_business_date,
      to: query.target_business_date,
    },
    explanation_object: {
      capability_id: query.capability_id,
      explanation_scope: 'service',
      reason_codes: reasonCodes,
      state_trace_refs: [],
      run_trace_refs: [],
    },
    state_trace_refs: [],
    run_trace_refs: [],
    served_at: new Date().toISOString(),
  };
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

function normalizeOwnerSurfacePayload(payload) {
  return {
    readiness_response: payload?.readiness_response ?? null,
    theme_service_response: payload?.theme_service_response ?? null,
    service_response: payload?.service_response ?? payload?.theme_service_response ?? null,
  };
}

export function createOwnerSideDataPlatformAdapter({
  pythonExecutable = 'python3',
  dataPlatformRoot = defaultDataPlatformRoot,
  defaultOrgId = null,
  defaultAppSecret = null,
  fixtureBundlePath = defaultFixtureBundlePath,
  fixtureBundlePaths = null,
  liveBaseUrl = null,
  liveAuthorization = null,
  liveToken = null,
  liveTimeoutMs = 15000,
  runCacheMaxEntries = 32,
  runCacheTtlMs = 5 * 60 * 1000,
  nowEpochMsFactory = () => Date.now(),
  runMemberInsightOwnerSurfaceImpl = null,
  runCapabilityExplanationOwnerSurfaceImpl = null,
} = {}) {
  const runCache = new Map();
  const adapterOptions = {
    defaultOrgId,
    defaultAppSecret,
    fixtureBundlePath,
    fixtureBundlePaths,
    liveBaseUrl,
    liveAuthorization,
    liveToken,
    liveTimeoutMs,
  };

  async function loadPublishedOwnerSurface(query, mode = 'base') {
    const context = resolveDataContext(query, adapterOptions);
    const cacheKey = JSON.stringify([
      mode,
      query.request_id,
      query.trace_ref,
      query.capability_id,
      query.target_scope_ref,
      context.org_id,
      context.requested_business_date,
      context.start_time,
      context.end_time,
      context.transport_kind,
      context.fixture_bundle_paths,
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

    let runPromise;
    if (
      mode === 'base'
      && context.requested_capability_id === 'navly.store.member_insight'
      && typeof runMemberInsightOwnerSurfaceImpl === 'function'
    ) {
      runPromise = Promise.resolve(runMemberInsightOwnerSurfaceImpl({
        pythonExecutable,
        dataPlatformRoot,
        input: context,
      })).then(normalizeOwnerSurfacePayload);
    } else if (
      mode === 'explanation'
      && typeof runCapabilityExplanationOwnerSurfaceImpl === 'function'
    ) {
      runPromise = Promise.resolve(runCapabilityExplanationOwnerSurfaceImpl({
        pythonExecutable,
        dataPlatformRoot,
        input: {
          ...context,
          requested_service_object_id: EXPLANATION_SERVICE_OBJECT_ID,
        },
      })).then(normalizeOwnerSurfacePayload);
    } else {
      runPromise = runPublishedOwnerSurface({
        pythonExecutable,
        dataPlatformRoot,
        input: {
          ...context,
          requested_service_object_id: mode === 'explanation'
            ? EXPLANATION_SERVICE_OBJECT_ID
            : publishedCapabilitySurfaceCatalog[context.requested_capability_id]?.defaultServiceObjectId ?? null,
        },
      }).then(normalizeOwnerSurfacePayload);
    }

    const retainedPromise = runPromise.catch((error) => {
      runCache.delete(cacheKey);
      throw error;
    });

    runCache.set(cacheKey, {
      promise: retainedPromise,
      created_at_epoch_ms: nowEpochMs,
    });
    enforceRunCacheBound(runCache, runCacheMaxEntries);

    return retainedPromise;
  }

  return {
    async queryCapabilityReadiness(query) {
      if (!publishedCapabilitySurfaceCatalog[query.capability_id]) {
        return buildUnsupportedReadiness(query);
      }

      const ownerSurface = await loadPublishedOwnerSurface(query, 'base');
      return ownerSurface.readiness_response;
    },

    async queryThemeService(query) {
      if (query.service_object_id === EXPLANATION_SERVICE_OBJECT_ID) {
        const explanationSurface = await loadPublishedOwnerSurface(query, 'explanation');
        return explanationSurface.service_response;
      }

      const capabilitySurface = publishedCapabilitySurfaceCatalog[query.capability_id];
      if (!capabilitySurface) {
        return buildScopeMismatchService(query, ['capability_scope_not_supported']);
      }

      if (query.service_object_id !== capabilitySurface.defaultServiceObjectId) {
        return buildScopeMismatchService(query);
      }

      const ownerSurface = await loadPublishedOwnerSurface(query, 'base');
      return ownerSurface.service_response;
    },
  };
}
