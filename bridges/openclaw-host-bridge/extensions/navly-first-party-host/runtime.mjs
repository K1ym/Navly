import fs from 'node:fs';
import path from 'node:path';
import { randomUUID } from 'node:crypto';
import { pathToFileURL } from 'node:url';

const DEFAULT_CHANNEL = 'wecom';
const DEFAULT_BUSINESS_TIMEZONE = 'Asia/Shanghai';
const DEFAULT_DATA_PLATFORM_ENV_PATH = '/etc/navly/data-platform.env';

const FIELD_SCHEMAS = Object.freeze({
  scope_ref: {
    type: 'string',
    description: 'Navly target scope_ref. Omit to let Navly fall back to the actor primary scope when available.',
  },
  business_date: {
    type: 'string',
    pattern: '^\\d{4}-\\d{2}-\\d{2}$',
    description: 'Business date in YYYY-MM-DD format.',
  },
  freshness_mode: {
    type: 'string',
    description: 'Freshness mode such as latest_usable.',
  },
  include_explanation: {
    type: 'boolean',
    description: 'Whether to include structured explanation/fallback metadata.',
  },
  time_window: {
    type: 'object',
    additionalProperties: false,
    properties: {
      start_time: { type: 'string' },
      end_time: { type: 'string' },
      from: { type: 'string' },
      to: { type: 'string' },
    },
    description: 'Optional explicit data time window.',
  },
  comparison_mode: {
    type: 'string',
    description: 'Optional comparison mode for summary-style tools.',
  },
  rerun_mode: {
    type: 'string',
    description: 'Optional rerun mode for operator tools.',
  },
  backfill_from: {
    type: 'string',
    pattern: '^\\d{4}-\\d{2}-\\d{2}$',
    description: 'Optional backfill start business date in YYYY-MM-DD format. Omit together with backfill_to to let Navly use the governed full-history start when configured.',
  },
  backfill_to: {
    type: 'string',
    pattern: '^\\d{4}-\\d{2}-\\d{2}$',
    description: 'Optional backfill end business date in YYYY-MM-DD format. Omit together with backfill_from to let Navly use the governed full-history end at the requested business date.',
  },
});

function readJson(filePath) {
  return JSON.parse(fs.readFileSync(filePath, 'utf8'));
}

function readText(filePath) {
  return fs.readFileSync(filePath, 'utf8');
}

function parseEnvFile(filePath) {
  const entries = {};
  if (!filePath || !fs.existsSync(filePath)) {
    return entries;
  }

  for (const rawLine of readText(filePath).split(/\r?\n/)) {
    const line = rawLine.trim();
    if (!line || line.startsWith('#') || !line.includes('=')) {
      continue;
    }

    const index = line.indexOf('=');
    const key = line.slice(0, index).trim();
    let value = line.slice(index + 1).trim();
    if (!key) {
      continue;
    }

    if ((value.startsWith('"') && value.endsWith('"')) || (value.startsWith("'") && value.endsWith("'"))) {
      value = value.slice(1, -1);
    }

    entries[key] = value;
  }

  return entries;
}

function normalizeOptionalString(value) {
  if (value === undefined || value === null) {
    return null;
  }
  const normalized = String(value).trim();
  return normalized ? normalized : null;
}

function buildBusinessDate(now = new Date(), timeZone = DEFAULT_BUSINESS_TIMEZONE) {
  const formatter = new Intl.DateTimeFormat('en-CA', {
    timeZone,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  });
  const parts = formatter.formatToParts(now);
  const lookup = Object.fromEntries(parts.map((part) => [part.type, part.value]));
  return `${lookup.year}-${lookup.month}-${lookup.day}`;
}

function resolveRepoRoot({ pluginConfig, moduleDir }) {
  const configured = normalizeOptionalString(pluginConfig.repoRoot) ?? normalizeOptionalString(process.env.NAVLY_REPO_ROOT);
  if (configured) {
    return path.resolve(configured);
  }

  const candidate = path.resolve(moduleDir, '..', '..', '..', '..');
  return candidate;
}

function resolveDataPlatformEnvPath(pluginConfig) {
  return normalizeOptionalString(pluginConfig.dataPlatformEnvPath)
    ?? normalizeOptionalString(process.env.NAVLY_DATA_PLATFORM_ENV_PATH)
    ?? DEFAULT_DATA_PLATFORM_ENV_PATH;
}

function loadPublicationManifest(repoRoot) {
  return readJson(
    path.join(
      repoRoot,
      'bridges',
      'openclaw-host-bridge',
      'tool-publication',
      'first-party-tool-publication.manifest.json',
    ),
  );
}

function buildToolParametersSchema(tool) {
  const properties = {};
  for (const fieldName of tool.allowed_input_fields ?? []) {
    properties[fieldName] = FIELD_SCHEMAS[fieldName] ?? {
      type: 'string',
      description: `Navly tool input field ${fieldName}.`,
    };
  }

  return {
    type: 'object',
    additionalProperties: false,
    properties,
  };
}

function normalizeToolInput(tool, params) {
  const allowed = new Set(tool.allowed_input_fields ?? []);
  const normalized = {};

  for (const [fieldName, value] of Object.entries(params ?? {})) {
    if (!allowed.has(fieldName) || value === undefined || value === null || value === '') {
      continue;
    }
    normalized[fieldName] = value;
  }

  return normalized;
}

function deriveMessageMode(context) {
  const sessionKey = normalizeOptionalString(context.sessionKey)?.toLowerCase() ?? '';
  if (sessionKey.includes(':group:')) {
    return 'group_message';
  }
  if (context.deliveryContext?.threadId !== undefined && context.deliveryContext?.threadId !== null) {
    return 'thread_message';
  }
  return 'direct_message';
}

function deriveChannelKind(context, pluginConfig) {
  return normalizeOptionalString(context.messageChannel)
    ?? normalizeOptionalString(context.deliveryContext?.channel)
    ?? normalizeOptionalString(pluginConfig.defaultChannel)
    ?? DEFAULT_CHANNEL;
}

function deriveChannelAccountRef({ context, pluginConfig, channelKind }) {
  const configured = normalizeOptionalString(pluginConfig.channelAccountRef);
  if (configured) {
    return configured;
  }
  const accountId = normalizeOptionalString(context.agentAccountId)
    ?? normalizeOptionalString(context.deliveryContext?.accountId)
    ?? 'default';
  return `openclaw-host-bridge:channel-account:${channelKind}-${accountId}`;
}

function deriveIdentityAliasNamespace({ channelKind, pluginConfig }) {
  return normalizeOptionalString(pluginConfig.identityAliasNamespace) ?? `${channelKind}_user_id`;
}

function deriveHostRefs({ requestId, context, channelKind, toolName }) {
  const agentId = normalizeOptionalString(context.agentId) ?? 'main';
  const sessionKey = normalizeOptionalString(context.sessionKey);
  const hostSessionRef = sessionKey ?? `openclaw:session:${agentId}:${channelKind}:${requestId}`;
  return {
    host_session_ref: hostSessionRef,
    host_workspace_ref: `openclaw:workspace:${agentId}`,
    host_conversation_ref: `openclaw:conversation:${sessionKey ?? requestId}`,
    host_message_ref: `openclaw:message:${toolName}:${requestId}`,
  };
}

function resolveScopeRef(toolInput, pluginConfig) {
  return normalizeOptionalString(toolInput.scope_ref) ?? normalizeOptionalString(pluginConfig.defaultScopeRef);
}

function resolveBusinessDate(toolInput, pluginConfig, nowFactory) {
  return normalizeOptionalString(toolInput.business_date)
    ?? buildBusinessDate(nowFactory(), normalizeOptionalString(pluginConfig.businessTimezone) ?? DEFAULT_BUSINESS_TIMEZONE);
}

function resolveOrgId({ scopeRef, pluginConfig, envConfig }) {
  const scopeOrgMap = pluginConfig.scopeOrgMap && typeof pluginConfig.scopeOrgMap === 'object'
    ? pluginConfig.scopeOrgMap
    : {};
  return normalizeOptionalString(scopeRef ? scopeOrgMap[scopeRef] : null)
    ?? normalizeOptionalString(pluginConfig.defaultOrgId)
    ?? normalizeOptionalString(envConfig.QINQIN_API_ORG_ID);
}

function defaultTransportKindForTool({ publishedTool, pluginConfig }) {
  return normalizeOptionalString(pluginConfig.transportKind)
    ?? (publishedTool?.host_agent_id === 'ops' ? 'live' : 'persisted');
}

function buildRuntimeDataContext({ toolInput, publishedTool, pluginConfig, envConfig, nowFactory }) {
  const businessDate = resolveBusinessDate(toolInput, pluginConfig, nowFactory);
  const scopeRef = resolveScopeRef(toolInput, pluginConfig);

  return {
    data_transport_kind: defaultTransportKindForTool({ publishedTool, pluginConfig }),
    data_persisted_serving_root: normalizeOptionalString(pluginConfig.persistedServingRoot)
      ?? normalizeOptionalString(process.env.NAVLY_DATA_PLATFORM_PERSISTED_SERVING_ROOT)
      ?? '/var/lib/navly/data-platform/serving-store',
    data_live_base_url: normalizeOptionalString(envConfig.QINQIN_API_BASE_URL)
      ?? normalizeOptionalString(envConfig.QINQIN_REAL_DATA_URL),
    data_live_authorization: normalizeOptionalString(envConfig.QINQIN_API_AUTHORIZATION),
    data_live_token: normalizeOptionalString(envConfig.QINQIN_API_TOKEN)
      ?? normalizeOptionalString(envConfig.QINQIN_REAL_DATA_TOKEN),
    data_live_timeout_ms: normalizeOptionalString(envConfig.QINQIN_API_REQUEST_TIMEOUT_MS),
    data_state_snapshot_path: normalizeOptionalString(pluginConfig.stateSnapshotPath)
      ?? normalizeOptionalString(envConfig.NAVLY_RUNTIME_STATE_SNAPSHOT_PATH)
      ?? normalizeOptionalString(envConfig.NAVLY_DATA_PLATFORM_STATE_SNAPSHOT_PATH),
    data_org_id: resolveOrgId({ scopeRef, pluginConfig, envConfig }),
    data_app_secret: normalizeOptionalString(pluginConfig.defaultAppSecret)
      ?? normalizeOptionalString(envConfig.QINQIN_API_APP_SECRET),
    data_fixture_bundle_path: normalizeOptionalString(pluginConfig.fixtureBundlePath)
      ?? normalizeOptionalString(envConfig.NAVLY_RUNTIME_FIXTURE_BUNDLE_PATH),
    data_window_start_time: `${businessDate} 00:00:00`,
    data_window_end_time: `${businessDate} 23:59:59`,
  };
}

function buildRawHostIngress({ toolName, toolInput, context, pluginConfig, nowFactory }) {
  const requesterSenderId = normalizeOptionalString(context.requesterSenderId);
  if (!requesterSenderId) {
    throw new Error('Navly first-party host tools require requesterSenderId from the active channel runtime.');
  }

  const now = nowFactory();
  const channelKind = deriveChannelKind(context, pluginConfig);
  const requestId = `navly-live-${toolName}-${randomUUID().replace(/-/g, '')}`;
  const traceRef = `navly:trace:${requestId}`;
  const hostRefs = deriveHostRefs({ requestId, context, channelKind, toolName });
  const scopeRef = resolveScopeRef(toolInput, pluginConfig);
  const businessDate = resolveBusinessDate(toolInput, pluginConfig, nowFactory);
  const targetBusinessDateHint = normalizeOptionalString(toolInput.business_date)
    ?? normalizeOptionalString(toolInput.backfill_to)
    ?? normalizeOptionalString(toolInput.backfill_from)
    ?? businessDate;

  return {
    request_id: requestId,
    trace_ref: traceRef,
    channel_kind: channelKind,
    message_mode: deriveMessageMode(context),
    channel_account_ref: deriveChannelAccountRef({ context, pluginConfig, channelKind }),
    ...hostRefs,
    peer_identity_evidence: [
      {
        alias_namespace: deriveIdentityAliasNamespace({ channelKind, pluginConfig }),
        alias_value: requesterSenderId,
      },
    ],
    message_text: `Navly first-party host tool ${toolName}`,
    target_scope_hint: scopeRef,
    target_business_date_hint: targetBusinessDateHint,
    response_channel_capabilities: {
      supports_text_reply: true,
      supports_private_reply: true,
      supports_thread_reply: context.deliveryContext?.threadId !== undefined && context.deliveryContext?.threadId !== null,
    },
    host_delivery_context: {
      dispatch_mode: context.deliveryContext?.threadId !== undefined && context.deliveryContext?.threadId !== null
        ? 'thread_reply'
        : 'direct_reply',
      target_ref: normalizeOptionalString(context.sessionKey)
        ?? normalizeOptionalString(context.deliveryContext?.to)
        ?? hostRefs.host_conversation_ref,
    },
    received_at: now.toISOString(),
  };
}

function buildToolResultPayload(result) {
  const runtimeResult = result.runtime_pipeline?.runtime_result_envelope ?? null;
  const firstReplyBlock = result.host_dispatch_result?.reply_blocks?.[0] ?? null;
  return {
    host_tool_name: result.published_tool.tool_name,
    capability_id: result.published_tool.capability_id,
    service_object_id: result.published_tool.service_object_id,
    dispatch_status: result.host_dispatch_result?.dispatch_status ?? null,
    result_status: runtimeResult?.result_status ?? null,
    selected_capability_id: runtimeResult?.selected_capability_id ?? result.published_tool.capability_id,
    selected_service_object_id: runtimeResult?.selected_service_object_id ?? result.published_tool.service_object_id,
    reason_codes: runtimeResult?.reason_codes ?? result.gate0_enforcement?.reason_codes ?? [],
    first_reply_block: firstReplyBlock,
    trace_refs: result.host_dispatch_result?.trace_refs ?? [],
  };
}

async function importLiveHandoff(repoRoot) {
  const modulePath = path.join(
    repoRoot,
    'bridges',
    'openclaw-host-bridge',
    'adapters',
    'openclaw',
    'first-party-live-handoff.mjs',
  );
  return import(pathToFileURL(modulePath).href);
}

export function createNavlyFirstPartyTools({
  repoRoot,
  pluginConfig = {},
  context = {},
  nowFactory = () => new Date(),
  liveHandoffRunner = null,
} = {}) {
  const manifest = loadPublicationManifest(repoRoot);
  const envConfig = parseEnvFile(resolveDataPlatformEnvPath(pluginConfig));
  const effectiveAgentId = normalizeOptionalString(context.agentId);
  const visibleTools = (manifest.tools ?? []).filter((tool) => {
    if (!effectiveAgentId) {
      return tool.host_agent_id === 'main';
    }
    return tool.host_agent_id === effectiveAgentId;
  });

  return visibleTools.map((tool) => ({
    name: tool.tool_name,
    label: tool.tool_name,
    description: `Navly first-party capability tool for ${tool.capability_id}.`,
    parameters: buildToolParametersSchema(tool),
    execute: async (_toolCallId, params) => {
      const normalizedToolInput = normalizeToolInput(tool, params);
      const runner = liveHandoffRunner ?? (await importLiveHandoff(repoRoot)).runFirstPartyLiveHostTool;
      const result = await runner({
        toolName: tool.tool_name,
        rawHostIngress: buildRawHostIngress({
          toolName: tool.tool_name,
          toolInput: normalizedToolInput,
          context,
          pluginConfig,
          nowFactory,
        }),
        toolInput: normalizedToolInput,
        hostAgentSelection: {
          agent_id: effectiveAgentId ?? tool.host_agent_id,
          carrier_ref: normalizeOptionalString(context.sessionKey),
        },
        runtimeDataContext: buildRuntimeDataContext({
          toolInput: normalizedToolInput,
          publishedTool: tool,
          pluginConfig,
          envConfig,
          nowFactory,
        }),
        now: nowFactory().toISOString(),
      });

      const payload = buildToolResultPayload(result);
      return {
        content: [{ type: 'text', text: JSON.stringify(payload, null, 2) }],
        details: {
          ...payload,
          live_handoff: result,
        },
      };
    },
  }));
}

export function createNavlyFirstPartyToolFactory({
  pluginConfig = {},
  nowFactory = () => new Date(),
  moduleDir,
  liveHandoffRunner = null,
} = {}) {
  const repoRoot = resolveRepoRoot({ pluginConfig, moduleDir });

  return (context) => createNavlyFirstPartyTools({
    repoRoot,
    pluginConfig,
    context,
    nowFactory,
    liveHandoffRunner,
  });
}
