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

const canonicalCapabilityId = 'navly.store.member_insight';
const canonicalServiceObjectId = 'navly.service.store.member_insight';

const memberInsightRunnerCode = String.raw`import json
import sys
from pathlib import Path

data_platform_root = Path(sys.argv[1]).resolve()
if str(data_platform_root) not in sys.path:
    sys.path.insert(0, str(data_platform_root))

from backbone_support.qinqin_substrate import FixtureQinqinTransport
from ingestion.member_insight_vertical_slice import run_member_insight_vertical_slice

args = json.loads(sys.argv[2])
fixture_bundle = json.loads(Path(args["fixture_bundle_path"]).read_text(encoding="utf-8"))
transport = FixtureQinqinTransport(fixture_bundle)
result = run_member_insight_vertical_slice(
    org_id=args["org_id"],
    start_time=args["start_time"],
    end_time=args["end_time"],
    requested_business_date=args["requested_business_date"],
    app_secret=args["app_secret"],
    transport=transport,
)

state = result["latest_state_artifacts"]["vertical_slice_backbone_state"]
summary = {
    "trace_ref": result["trace_ref"],
    "capability_id": result["capability_id"],
    "service_object_id": result["service_object_id"],
    "backbone_status": state["backbone_status"],
    "latest_usable_business_date": state["requested_business_date"],
    "state_trace_ref": state["state_trace_ref"],
    "run_trace_ref": result["historical_run_truth"]["ingestion_run"]["run_trace_ref"],
    "updated_at": state["updated_at"],
    "service_object": {
        "customer_count": len(result["canonical_artifacts"]["customer"]),
        "customer_card_count": len(result["canonical_artifacts"]["customer_card"]),
        "consume_bill_count": len(result["canonical_artifacts"]["consume_bill"]),
        "consume_bill_payment_count": len(result["canonical_artifacts"]["consume_bill_payment"]),
        "consume_bill_info_count": len(result["canonical_artifacts"]["consume_bill_info"]),
    },
}
print(json.dumps(summary, ensure_ascii=False))`;

function asNonEmptyString(value) {
  return typeof value === 'string' && value.trim().length > 0 ? value.trim() : null;
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

  const startTime = asNonEmptyString(contextFromQuery.start_time) ?? `${targetBusinessDate} 00:00:00`;
  const endTime = asNonEmptyString(contextFromQuery.end_time) ?? `${targetBusinessDate} 23:59:59`;

  return {
    org_id: orgId,
    requested_business_date: targetBusinessDate,
    start_time: startTime,
    end_time: endTime,
    app_secret: appSecret,
    fixture_bundle_path: fixtureBundlePath,
  };
}

async function runMemberInsightBackbone({
  pythonExecutable,
  dataPlatformRoot,
  input,
}) {
  const pythonPath = [dataPlatformRoot, process.env.PYTHONPATH].filter(Boolean).join(path.delimiter);
  const { stdout, stderr } = await execFileAsync(
    pythonExecutable,
    [
      '-c',
      memberInsightRunnerCode,
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

export function createOwnerSideDataPlatformAdapter({
  pythonExecutable = 'python3',
  dataPlatformRoot = defaultDataPlatformRoot,
  defaultOrgId = null,
  defaultAppSecret = null,
  fixtureBundlePath = defaultFixtureBundlePath,
} = {}) {
  const runCache = new Map();

  async function loadMemberInsightSummary(query) {
    const context = resolveDataContext(query, {
      defaultOrgId,
      defaultAppSecret,
      fixtureBundlePath,
    });

    const cacheKey = JSON.stringify([
      context.org_id,
      context.requested_business_date,
      context.start_time,
      context.end_time,
      context.fixture_bundle_path,
    ]);
    if (!runCache.has(cacheKey)) {
      runCache.set(cacheKey, runMemberInsightBackbone({
        pythonExecutable,
        dataPlatformRoot,
        input: context,
      }));
    }

    return runCache.get(cacheKey);
  }

  return {
    async queryCapabilityReadiness(query) {
      if (query.capability_id !== canonicalCapabilityId) {
        return buildUnsupportedReadiness(query);
      }

      const summary = await loadMemberInsightSummary(query);
      const readinessStatus = summary.backbone_status === 'backbone_ready' ? 'ready' : 'pending';

      return {
        request_id: query.request_id,
        trace_ref: query.trace_ref,
        capability_id: query.capability_id,
        readiness_status: readinessStatus,
        evaluated_scope_ref: query.target_scope_ref,
        requested_business_date: query.target_business_date,
        latest_usable_business_date: summary.latest_usable_business_date ?? query.target_business_date,
        reason_codes: readinessStatus === 'ready' ? [] : ['missing_dependency'],
        blocking_dependencies: [],
        state_trace_refs: summary.state_trace_ref ? [summary.state_trace_ref] : [],
        run_trace_refs: summary.run_trace_ref ? [summary.run_trace_ref] : [],
        evaluated_at: summary.updated_at ?? new Date().toISOString(),
      };
    },

    async queryThemeService(query) {
      if (query.capability_id !== canonicalCapabilityId || query.service_object_id !== canonicalServiceObjectId) {
        return buildScopeMismatchService(query);
      }

      const summary = await loadMemberInsightSummary(query);
      if (summary.backbone_status !== 'backbone_ready') {
        return buildScopeMismatchService(query, ['missing_dependency']);
      }

      return {
        request_id: query.request_id,
        trace_ref: query.trace_ref,
        capability_id: query.capability_id,
        service_object_id: query.service_object_id,
        service_status: 'served',
        service_object: {
          ...summary.service_object,
          capability_id: query.capability_id,
          service_object_id: query.service_object_id,
          target_scope_ref: query.target_scope_ref,
          target_business_date: query.target_business_date,
        },
        data_window: {
          from: summary.latest_usable_business_date ?? query.target_business_date,
          to: summary.latest_usable_business_date ?? query.target_business_date,
        },
        explanation_object: null,
        state_trace_refs: summary.state_trace_ref ? [summary.state_trace_ref] : [],
        run_trace_refs: summary.run_trace_ref ? [summary.run_trace_ref] : [],
        served_at: summary.updated_at ?? new Date().toISOString(),
      };
    },
  };
}
