import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import {
  assertCapabilityId,
  assertServiceObjectId,
  ensureObject,
  normalizeOptionalString,
  uniqueStrings,
} from '../adapters/openclaw/bridge-shared-alignment.mjs';

const moduleDir = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(moduleDir, '..', '..', '..');

const publicationSourceRefs = Object.freeze({
  capability_registry_path: 'platforms/data-platform/directory/capability-registry.seed.json',
  capability_service_binding_path: 'platforms/data-platform/directory/capability-service-bindings.seed.json',
  auth_capability_vocabulary_path: 'platforms/auth-kernel/policy-catalog/capability-vocabulary.seed.json',
  host_skill_surface_path: 'bridges/openclaw-host-bridge/tool-publication/host-skill-surface.seed.json',
  host_tool_surface_path: 'bridges/openclaw-host-bridge/tool-publication/host-tool-surface.seed.json',
});

const defaultPaths = Object.freeze({
  capabilityRegistry: path.join(repoRoot, publicationSourceRefs.capability_registry_path),
  capabilityServiceBinding: path.join(repoRoot, publicationSourceRefs.capability_service_binding_path),
  authCapabilityVocabulary: path.join(repoRoot, publicationSourceRefs.auth_capability_vocabulary_path),
  hostSkillSurface: path.join(repoRoot, publicationSourceRefs.host_skill_surface_path),
  hostToolSurface: path.join(repoRoot, publicationSourceRefs.host_tool_surface_path),
  publicationManifest: path.join(
    repoRoot,
    'bridges',
    'openclaw-host-bridge',
    'tool-publication',
    'first-party-tool-publication.manifest.json',
  ),
});

function readJson(filePath) {
  return JSON.parse(fs.readFileSync(filePath, 'utf8'));
}

function cloneJson(value) {
  if (typeof structuredClone === 'function') {
    return structuredClone(value);
  }
  return JSON.parse(JSON.stringify(value));
}

function normalizeStringArray(values, label) {
  const normalized = uniqueStrings(values);
  if (!normalized.length) {
    throw new Error(`${label} must contain at least one non-empty string`);
  }
  return normalized;
}

function normalizeHostSkillEntry(skill) {
  const normalizedSkill = ensureObject('host_skill_entry', skill);
  return {
    skill_id: normalizeOptionalString(normalizedSkill.skill_id),
    display_name: normalizeOptionalString(normalizedSkill.display_name),
    tool_names: normalizeStringArray(normalizedSkill.tool_names, `tool_names for ${normalizedSkill.skill_id}`),
    host_agent_id: normalizeOptionalString(normalizedSkill.host_agent_id) ?? 'main',
    surface_kind: normalizeOptionalString(normalizedSkill.surface_kind) ?? 'business',
    user_group: normalizeOptionalString(normalizedSkill.user_group) ?? 'store_manager_or_staff',
  };
}

function normalizeHostToolEntry(tool, requiredContextFields) {
  const normalizedTool = ensureObject('host_tool_entry', tool);

  const capabilityId = normalizeOptionalString(normalizedTool.capability_id);
  const serviceObjectId = normalizeOptionalString(normalizedTool.service_object_id);
  assertCapabilityId(capabilityId);
  assertServiceObjectId(serviceObjectId);

  return {
    tool_name: normalizeOptionalString(normalizedTool.tool_name),
    skill_ids: normalizeStringArray(normalizedTool.skill_ids, `skill_ids for ${normalizedTool.tool_name}`),
    host_agent_id: normalizeOptionalString(normalizedTool.host_agent_id) ?? 'main',
    visibility_scope: normalizeOptionalString(normalizedTool.visibility_scope) ?? 'host_visible',
    capability_id: capabilityId,
    service_object_id: serviceObjectId,
    allowed_input_fields: normalizeStringArray(
      normalizedTool.allowed_input_fields,
      `allowed_input_fields for ${normalizedTool.tool_name}`,
    ),
    required_context_fields: normalizeStringArray(
      normalizedTool.required_context_fields ?? requiredContextFields,
      `required_context_fields for ${normalizedTool.tool_name}`,
    ),
    operator_only: Boolean(normalizedTool.operator_only),
  };
}

export function loadHostSkillSurface(skillSurfacePath = defaultPaths.hostSkillSurface) {
  const rawSurface = ensureObject('host_skill_surface', readJson(skillSurfacePath));
  return {
    surface_name: normalizeOptionalString(rawSurface.surface_name) ?? 'navly_first_party_host_skill_surface',
    status: normalizeOptionalString(rawSurface.status) ?? 'phase_1_closeout',
    skills: (rawSurface.skills ?? []).map((skill) => normalizeHostSkillEntry(skill)),
  };
}

export function loadHostToolSurface(toolSurfacePath = defaultPaths.hostToolSurface) {
  const rawSurface = ensureObject('host_tool_surface', readJson(toolSurfacePath));
  const requiredContextFields = normalizeStringArray(
    rawSurface.required_context_fields ?? ['request_id', 'trace_ref', 'access_context_envelope', 'decision_ref'],
    'host_tool_surface.required_context_fields',
  );

  return {
    surface_name: normalizeOptionalString(rawSurface.surface_name) ?? 'navly_first_party_host_tool_surface',
    status: normalizeOptionalString(rawSurface.status) ?? 'phase_1_closeout',
    required_context_fields: requiredContextFields,
    tools: (rawSurface.tools ?? []).map((tool) => normalizeHostToolEntry(tool, requiredContextFields)),
  };
}

function indexBy(entries, keyName) {
  const index = new Map();
  for (const entry of entries) {
    if (entry?.[keyName]) {
      index.set(entry[keyName], entry);
    }
  }
  return index;
}

function buildPublishedTools({ toolSurface, capabilityRegistry, capabilityServiceBinding, authCapabilityVocabulary }) {
  const capabilityEntries = indexBy(capabilityRegistry.entries ?? [], 'capability_id');
  const serviceBindingEntries = indexBy(capabilityServiceBinding.entries ?? [], 'service_object_id');
  const authCapabilityEntries = indexBy(authCapabilityVocabulary.capabilities ?? [], 'capability_id');

  return toolSurface.tools.map((tool) => {
    const capabilityEntry = capabilityEntries.get(tool.capability_id);
    if (!capabilityEntry) {
      throw new Error(`host tool ${tool.tool_name} references unknown capability_id ${tool.capability_id}`);
    }

    const serviceBindingEntry = serviceBindingEntries.get(tool.service_object_id);
    if (!serviceBindingEntry) {
      throw new Error(`host tool ${tool.tool_name} references unknown service_object_id ${tool.service_object_id}`);
    }

    if (serviceBindingEntry.capability_id !== tool.capability_id) {
      throw new Error(
        `host tool ${tool.tool_name} service binding ${tool.service_object_id} does not belong to capability ${tool.capability_id}`,
      );
    }

    const authCapabilityEntry = authCapabilityEntries.get(tool.capability_id);
    if (!authCapabilityEntry) {
      throw new Error(`host tool ${tool.tool_name} capability ${tool.capability_id} is missing from auth capability vocabulary`);
    }

    return {
      ...tool,
      capability_status: normalizeOptionalString(capabilityEntry.status) ?? 'unknown',
      service_binding_status: normalizeOptionalString(serviceBindingEntry.status) ?? 'unknown',
      capability_kind: normalizeOptionalString(authCapabilityEntry.capability_kind) ?? 'data_read',
      owner_module: 'runtime',
    };
  });
}

function buildPublishedSkills({ skillSurface, publishedTools }) {
  const publishedToolsByName = indexBy(publishedTools, 'tool_name');

  return skillSurface.skills.map((skill) => {
    skill.tool_names.forEach((toolName) => {
      if (!publishedToolsByName.has(toolName)) {
        throw new Error(`host skill ${skill.skill_id} references unpublished tool ${toolName}`);
      }
    });

    return {
      ...skill,
      published_tool_count: skill.tool_names.length,
    };
  });
}

export function discoverFirstPartyHostSurface({
  skillSurface = loadHostSkillSurface(),
  toolSurface = loadHostToolSurface(),
  capabilityRegistry = readJson(defaultPaths.capabilityRegistry),
  capabilityServiceBinding = readJson(defaultPaths.capabilityServiceBinding),
  authCapabilityVocabulary = readJson(defaultPaths.authCapabilityVocabulary),
} = {}) {
  const publishedTools = buildPublishedTools({
    toolSurface,
    capabilityRegistry,
    capabilityServiceBinding,
    authCapabilityVocabulary,
  });

  const publishedSkills = buildPublishedSkills({
    skillSurface,
    publishedTools,
  });

  return {
    surface_name: 'navly_first_party_host_surface',
    status: 'phase_1_closeout',
    skill_count: publishedSkills.length,
    tool_count: publishedTools.length,
    generated_from: cloneJson(publicationSourceRefs),
    skills: publishedSkills,
    tools: publishedTools,
  };
}

function buildHostToolRegistrations(publishedTools) {
  return publishedTools.map((tool) => ({
    tool_name: tool.tool_name,
    capability_id: tool.capability_id,
    service_object_id: tool.service_object_id,
    host_agent_id: tool.host_agent_id,
    visibility_scope: tool.visibility_scope,
    registration_status: 'ready',
  }));
}

export function buildFirstPartyToolPublicationManifest(options = {}) {
  const surface = discoverFirstPartyHostSurface(options);

  return {
    object_name: 'tool_publication_manifest',
    object_scope: 'bridge_local',
    publication_version: 'phase1-first-party-closeout',
    generated_from: surface.generated_from,
    skill_count: surface.skill_count,
    tool_count: surface.tool_count,
    skills: surface.skills,
    tools: surface.tools.map((tool) => ({
      tool_name: tool.tool_name,
      skill_ids: tool.skill_ids,
      host_agent_id: tool.host_agent_id,
      visibility_scope: tool.visibility_scope,
      operator_only: tool.operator_only,
      capability_id: tool.capability_id,
      service_object_id: tool.service_object_id,
      capability_status: tool.capability_status,
      service_binding_status: tool.service_binding_status,
      capability_kind: tool.capability_kind,
      owner_module: tool.owner_module,
      required_context_fields: tool.required_context_fields,
      allowed_input_fields: tool.allowed_input_fields,
      runtime_handoff: {
        requested_capability_id: tool.capability_id,
        requested_service_object_id: tool.service_object_id,
      },
    })),
    host_tool_registrations: buildHostToolRegistrations(surface.tools),
  };
}

export function findPublishedTool({ toolName, manifest = buildFirstPartyToolPublicationManifest() }) {
  return manifest.tools.find((tool) => tool.tool_name === toolName) ?? null;
}

export function readCommittedFirstPartyToolPublicationManifest(
  manifestPath = defaultPaths.publicationManifest,
) {
  return readJson(manifestPath);
}
