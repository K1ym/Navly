import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import {
  assertCapabilityId,
  assertServiceObjectId,
  buildHostLocalRef,
  ensureObject,
  uniqueStrings,
} from '../adapters/openclaw/bridge-shared-alignment.mjs';

const moduleDir = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(moduleDir, '..', '..', '..');
const defaultCapabilityRegistryPath = path.join(
  repoRoot,
  'platforms',
  'data-platform',
  'directory',
  'capability-registry.seed.json',
);
const defaultServiceBindingsPath = path.join(
  repoRoot,
  'platforms',
  'data-platform',
  'directory',
  'capability-service-bindings.seed.json',
);

const RUNTIME_REQUEST_SCHEMA_REF = 'shared/contracts/interaction/runtime_request_envelope.schema.json';
const RUNTIME_RESULT_SCHEMA_REF = 'shared/contracts/interaction/runtime_result_envelope.schema.json';
const EXPLANATION_SERVICE_OBJECT_ID = 'navly.service.system.capability_explanation';
const EXPLANATION_CAPABILITY_ID = 'navly.system.capability_explanation';

function readJson(filePath) {
  return JSON.parse(fs.readFileSync(filePath, 'utf8'));
}

function buildToolName(capabilityId) {
  return capabilityId.replace(/\./g, '_');
}

function buildToolDescription(capabilityId) {
  return `Capability-first host tool for ${capabilityId}.`;
}

function buildHostVisibleTool({
  capabilityId,
  serviceObjectId,
  supportedServiceObjectIds,
  publicationVersion,
}) {
  assertCapabilityId(capabilityId);
  assertServiceObjectId(serviceObjectId);
  const normalizedSupportedServiceObjectIds = uniqueStrings([
    serviceObjectId,
    ...supportedServiceObjectIds,
  ]);
  normalizedSupportedServiceObjectIds.forEach((value) => assertServiceObjectId(value));

  return {
    tool_name: buildToolName(capabilityId),
    capability_id: capabilityId,
    service_object_id: serviceObjectId,
    supported_service_object_ids: normalizedSupportedServiceObjectIds,
    visibility_scope: 'host_visible',
    owner_module: 'runtime',
    publication_kind: 'capability_tool',
    tool_description: buildToolDescription(capabilityId),
    input_schema_ref: RUNTIME_REQUEST_SCHEMA_REF,
    output_schema_ref: RUNTIME_RESULT_SCHEMA_REF,
    publication_version: publicationVersion,
  };
}

function buildExplanationCapabilityTool(publicationVersion) {
  return buildHostVisibleTool({
    capabilityId: EXPLANATION_CAPABILITY_ID,
    serviceObjectId: EXPLANATION_SERVICE_OBJECT_ID,
    supportedServiceObjectIds: [EXPLANATION_SERVICE_OBJECT_ID],
    publicationVersion,
  });
}

function loadPublishedCapabilityToolEntries({
  capabilityRegistryPath = defaultCapabilityRegistryPath,
  serviceBindingsPath = defaultServiceBindingsPath,
} = {}) {
  const capabilityRegistry = readJson(capabilityRegistryPath);
  const serviceBindings = readJson(serviceBindingsPath);
  const serviceBindingByCapabilityId = new Map(
    (serviceBindings.entries ?? [])
      .filter((entry) => entry.status === 'owner_surface_published')
      .map((entry) => [entry.capability_id, entry]),
  );

  return (capabilityRegistry.entries ?? [])
    .filter((entry) => entry.status === 'owner_surface_published')
    .map((entry) => {
      const binding = serviceBindingByCapabilityId.get(entry.capability_id);
      if (!binding) {
        return null;
      }
      return {
        capability_id: entry.capability_id,
        default_service_object_id: binding.service_object_id,
        include_explanation_supported: binding.include_explanation_supported === true,
      };
    })
    .filter(Boolean);
}

export function buildCapabilityToolPublicationManifest({
  capabilityEntries = loadPublishedCapabilityToolEntries(),
  publicationVersion = 'phase-1-capability-publication-v1',
  now = new Date().toISOString(),
} = {}) {
  const tools = capabilityEntries.map((entry) => buildHostVisibleTool({
    capabilityId: entry.capability_id,
    serviceObjectId: entry.default_service_object_id,
    supportedServiceObjectIds: entry.include_explanation_supported
      ? [EXPLANATION_SERVICE_OBJECT_ID]
      : [],
    publicationVersion,
  }));

  tools.push(buildExplanationCapabilityTool(publicationVersion));

  return {
    object_name: 'tool_publication_manifest',
    object_scope: 'bridge_local',
    publication_version: publicationVersion,
    publication_status: 'phase_1_capability_oriented',
    publication_controls: {
      refresh_operation_kind: 'refresh',
      warmup_operation_kind: 'warmup',
    },
    tools,
    published_at: now,
  };
}

export function buildCapabilityToolPublicationWarmup({
  toolPublicationManifest,
  now = new Date().toISOString(),
}) {
  const manifest = ensureObject('toolPublicationManifest', toolPublicationManifest);
  const tools = Array.isArray(manifest.tools) ? manifest.tools : [];

  return {
    object_name: 'tool_publication_warmup',
    object_scope: 'bridge_local',
    warmup_kind: 'phase_1_capability_publication_warmup',
    publication_version: manifest.publication_version,
    tool_names: tools.map((entry) => entry.tool_name),
    capability_ids: tools.map((entry) => entry.capability_id),
    requested_at: now,
  };
}

export function buildCapabilityToolPublicationRefresh({
  previousManifest = null,
  nextManifest,
  now = new Date().toISOString(),
}) {
  const manifest = ensureObject('nextManifest', nextManifest);
  const nextTools = Array.isArray(manifest.tools) ? manifest.tools : [];
  const previousTools = Array.isArray(previousManifest?.tools) ? previousManifest.tools : [];
  const previousToolMap = new Map(previousTools.map((entry) => [entry.tool_name, entry]));
  const nextToolMap = new Map(nextTools.map((entry) => [entry.tool_name, entry]));

  const addedToolNames = nextTools
    .map((entry) => entry.tool_name)
    .filter((toolName) => !previousToolMap.has(toolName));
  const removedToolNames = previousTools
    .map((entry) => entry.tool_name)
    .filter((toolName) => !nextToolMap.has(toolName));
  const changedToolNames = nextTools
    .map((entry) => entry.tool_name)
    .filter((toolName) => previousToolMap.has(toolName))
    .filter((toolName) => JSON.stringify(previousToolMap.get(toolName)) !== JSON.stringify(nextToolMap.get(toolName)));

  return {
    object_name: 'tool_publication_refresh_result',
    object_scope: 'bridge_local',
    refresh_ref: buildHostLocalRef('tool-publication-refresh', manifest.publication_version, now),
    refresh_kind: 'phase_1_capability_publication_refresh',
    publication_version: manifest.publication_version,
    refresh_status: 'refreshed',
    added_tool_names: addedToolNames,
    removed_tool_names: removedToolNames,
    changed_tool_names: changedToolNames,
    published_tool_names: nextTools.map((entry) => entry.tool_name),
    refreshed_at: now,
  };
}
