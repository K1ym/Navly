import fs from 'node:fs';
import path from 'node:path';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import { fileURLToPath } from 'node:url';

const execFileAsync = promisify(execFile);
const moduleDir = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(moduleDir, '..', '..', '..');
const defaultDataPlatformRoot = path.join(repoRoot, 'platforms', 'data-platform');

const CAPABILITY_EXPLANATION_CAPABILITY_ID = 'navly.system.capability_explanation';
const CAPABILITY_EXPLANATION_SERVICE_OBJECT_ID = 'navly.service.system.capability_explanation';

function readJson(filePath) {
  return JSON.parse(fs.readFileSync(filePath, 'utf8'));
}

function loadSupportedOwnerSurfaceRegistry(dataPlatformRoot) {
  const capabilityRegistry = readJson(path.join(dataPlatformRoot, 'directory', 'capability-registry.seed.json'));
  const serviceBindingRegistry = readJson(path.join(dataPlatformRoot, 'directory', 'capability-service-bindings.seed.json'));
  const capabilities = new Set(
    (capabilityRegistry.entries ?? [])
      .filter((entry) => !String(entry?.status ?? '').startsWith('retired'))
      .map((entry) => entry.capability_id),
  );
  const serviceBindingByCapability = new Map(
    (serviceBindingRegistry.entries ?? [])
      .filter((entry) => !String(entry?.status ?? '').startsWith('retired'))
      .map((entry) => [entry.capability_id, entry.service_object_id]),
  );
  return {
    supportedCapabilityIds: capabilities,
    serviceBindingByCapability,
  };
}

const phase1OwnerSurfaceCode = String.raw`import json
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
from tests.support.qinqin_governance_fixture_builder import build_aligned_fixture_pages_by_endpoint
from workflows.qinqin_phase1_owner_surface import build_qinqin_phase1_owner_surface

args = json.loads(sys.argv[2])
transport_kind = args.get("transport_kind") or "fixture"
if transport_kind == "fixture":
    fixture_bundle_path = args.get("fixture_bundle_path")
    if fixture_bundle_path:
        fixture_bundle = json.loads(Path(fixture_bundle_path).read_text(encoding="utf-8"))
    else:
        fixture_bundle = build_aligned_fixture_pages_by_endpoint(value_suffix="runtime")
    transport = FixtureQinqinTransport(fixture_bundle)
else:
    live_timeout_ms = args.get("live_timeout_ms") or DEFAULT_LIVE_TIMEOUT_MS
    transport = LiveQinqinTransport(
        base_url=args["live_base_url"],
        timeout_ms=int(live_timeout_ms),
        authorization=args.get("live_authorization"),
        token=args.get("live_token"),
    )

result = build_qinqin_phase1_owner_surface(
    request_id=args["request_id"],
    trace_ref=args["trace_ref"],
    target_scope_ref=args["target_scope_ref"],
    target_business_date=args["requested_business_date"],
    requested_capability_id=args["capability_id"],
    requested_service_object_id=args["service_object_id"],
    org_id=args.get("org_id"),
    start_time=args.get("start_time"),
    end_time=args.get("end_time"),
    app_secret=args.get("app_secret"),
    transport=transport,
    explanation_context=args.get("explanation_context") or {},
)
print(json.dumps({
    "readiness_response": result["readiness_response"],
    "theme_service_response": result["theme_service_response"],
}, ensure_ascii=False))`;

function asNonEmptyString(value) {
  return typeof value === 'string' && value.trim().length > 0 ? value.trim() : null;
}

function resolveDataContext(query, adapterOptions) {
  const contextFromQuery = query?.extensions?.data_adapter_context ?? {};
  const explanationContext = query?.extensions?.explanation_context ?? {};
  const capabilityId = asNonEmptyString(query?.capability_id);
  const targetBusinessDate = asNonEmptyString(query?.target_business_date);
  if (!capabilityId) {
    throw new Error('owner-side data adapter requires capability_id');
  }
  if (!targetBusinessDate) {
    throw new Error('owner-side data adapter requires target_business_date');
  }

  const requiresDataTransport = capabilityId !== CAPABILITY_EXPLANATION_CAPABILITY_ID;
  const orgId = asNonEmptyString(contextFromQuery.org_id) ?? asNonEmptyString(adapterOptions.defaultOrgId);
  const appSecret = asNonEmptyString(contextFromQuery.app_secret)
    ?? asNonEmptyString(adapterOptions.defaultAppSecret)
    ?? asNonEmptyString(process.env.NAVLY_RUNTIME_DATA_APP_SECRET);

  if (requiresDataTransport && !orgId) {
    throw new Error('owner-side data adapter requires org_id');
  }
  if (requiresDataTransport && !appSecret) {
    throw new Error('owner-side data adapter requires app_secret');
  }

  const fixtureBundlePath = asNonEmptyString(contextFromQuery.fixture_bundle_path)
    ?? asNonEmptyString(adapterOptions.fixtureBundlePath)
    ?? null;
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
    capability_id: capabilityId,
    service_object_id: asNonEmptyString(query?.service_object_id)
      ?? adapterOptions.serviceBindingByCapability.get(capabilityId)
      ?? CAPABILITY_EXPLANATION_SERVICE_OBJECT_ID,
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
    explanation_context: explanationContext,
  };
}

async function runPhase1OwnerSurface({
  pythonExecutable,
  dataPlatformRoot,
  input,
}) {
  const pythonPath = [dataPlatformRoot, process.env.PYTHONPATH].filter(Boolean).join(path.delimiter);
  const { stdout, stderr } = await execFileAsync(
    pythonExecutable,
    [
      '-c',
      phase1OwnerSurfaceCode,
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
    evaluated_at: new Date().toISOString(),
  };
}

function buildScopeMismatchService(query, reasonCodes = ['scope_out_of_contract']) {
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

export function createOwnerSideDataPlatformAdapter({
  pythonExecutable = 'python3',
  dataPlatformRoot = defaultDataPlatformRoot,
  defaultOrgId = null,
  defaultAppSecret = null,
  fixtureBundlePath = null,
  liveBaseUrl = null,
  liveAuthorization = null,
  liveToken = null,
  liveTimeoutMs = 15000,
  runCacheMaxEntries = 32,
  runCacheTtlMs = 5 * 60 * 1000,
  nowEpochMsFactory = () => Date.now(),
  runPhase1OwnerSurfaceImpl = runPhase1OwnerSurface,
} = {}) {
  const runCache = new Map();
  const { supportedCapabilityIds, serviceBindingByCapability } = loadSupportedOwnerSurfaceRegistry(dataPlatformRoot);

  async function loadPhase1OwnerSurface(query) {
    const context = resolveDataContext(query, {
      defaultOrgId,
      defaultAppSecret,
      fixtureBundlePath,
      liveBaseUrl,
      liveAuthorization,
      liveToken,
      liveTimeoutMs,
      serviceBindingByCapability,
    });

    const cacheKey = JSON.stringify([
      query.request_id,
      query.trace_ref,
      query.target_scope_ref,
      context.capability_id,
      context.service_object_id,
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
      context.explanation_context,
    ]);

    const nowEpochMsCandidate = Number(nowEpochMsFactory());
    const nowEpochMs = Number.isFinite(nowEpochMsCandidate) ? nowEpochMsCandidate : Date.now();
    pruneExpiredRunCache(runCache, nowEpochMs, runCacheTtlMs);

    const cachedEntry = runCache.get(cacheKey);
    if (cachedEntry?.promise) {
      return cachedEntry.promise;
    }

    const runPromise = runPhase1OwnerSurfaceImpl({
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

  return {
    async queryCapabilityReadiness(query) {
      if (!supportedCapabilityIds.has(query.capability_id)) {
        return buildUnsupportedReadiness(query);
      }

      const ownerSurface = await loadPhase1OwnerSurface(query);
      return ownerSurface.readiness_response;
    },

    async queryThemeService(query) {
      if (!supportedCapabilityIds.has(query.capability_id)) {
        return buildScopeMismatchService(query, ['capability_not_registered']);
      }

      const expectedServiceObjectId = serviceBindingByCapability.get(query.capability_id);
      if (!expectedServiceObjectId || query.service_object_id !== expectedServiceObjectId) {
        return buildScopeMismatchService(query);
      }

      const ownerSurface = await loadPhase1OwnerSurface(query);
      return ownerSurface.theme_service_response;
    },
  };
}
