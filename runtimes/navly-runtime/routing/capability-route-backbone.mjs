import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import {
  assertCapabilityId,
  assertServiceObjectId,
  assertScopeRef,
  normalizeReasonCodes,
} from '../contracts/shared-contract-alignment.mjs';

const moduleDir = path.dirname(fileURLToPath(import.meta.url));
const defaultRegistryPath = path.join(moduleDir, 'capability-route-registry.seed.json');
const capabilityRouteRegistryCache = new Map();

function readJson(filePath) {
  return JSON.parse(fs.readFileSync(filePath, 'utf8'));
}

function normalizeMatchText(value) {
  return String(value ?? '').trim().toLowerCase();
}

function splitInputTokens(userInputText) {
  const normalized = normalizeMatchText(userInputText);
  if (!normalized) {
    return [];
  }

  return normalized
    .replace(/[^\p{L}\p{N}_.:-]+/gu, ' ')
    .split(/\s+/)
    .filter((token) => token.length > 0);
}

function normalizeEntry(entry) {
  assertCapabilityId(entry.capability_id);
  assertServiceObjectId(entry.default_service_object_id);

  const supportedServiceObjectIds = [
    entry.default_service_object_id,
    ...(Array.isArray(entry.supported_service_object_ids) ? entry.supported_service_object_ids : []),
  ].filter((value, index, array) => array.indexOf(value) === index);

  supportedServiceObjectIds.forEach((serviceObjectId) => assertServiceObjectId(serviceObjectId));

  return {
    route_id: entry.route_id,
    match_mode: entry.match_mode ?? 'explicit_or_match_tokens',
    match_tokens: Array.isArray(entry.match_tokens)
      ? entry.match_tokens.map((token) => normalizeMatchText(token)).filter((token) => token.length > 0)
      : [],
    capability_id: entry.capability_id,
    default_service_object_id: entry.default_service_object_id,
    supported_service_object_ids: supportedServiceObjectIds,
    status: entry.status,
  };
}

function cloneRegistry(registry) {
  if (typeof structuredClone === 'function') {
    return structuredClone(registry);
  }
  return JSON.parse(JSON.stringify(registry));
}

function supportsMatchTokens(entry) {
  return entry.match_mode === 'match_tokens' || entry.match_mode === 'explicit_or_match_tokens';
}

function pickServiceObjectId({ entry, requestedServiceObjectId }) {
  if (!requestedServiceObjectId) {
    return {
      selectedServiceObjectId: entry.default_service_object_id,
      routeReasonCodes: [],
    };
  }

  if (entry.supported_service_object_ids.includes(requestedServiceObjectId)) {
    return {
      selectedServiceObjectId: requestedServiceObjectId,
      routeReasonCodes: [],
    };
  }

  return {
    selectedServiceObjectId: entry.default_service_object_id,
    routeReasonCodes: ['runtime.route.service_binding_defaulted'],
  };
}

function buildResolvedRoute({ entry, requestedServiceObjectId }) {
  const { selectedServiceObjectId, routeReasonCodes } = pickServiceObjectId({
    entry,
    requestedServiceObjectId,
  });

  return {
    route_status: 'resolved',
    route_id: entry.route_id,
    selected_capability_id: entry.capability_id,
    selected_service_object_id: selectedServiceObjectId,
    reason_codes: routeReasonCodes,
  };
}

function resolveByRequestedCapability({ entries, requestedCapabilityId, requestedServiceObjectId }) {
  if (!requestedCapabilityId) {
    return null;
  }

  const match = entries.find((entry) => entry.capability_id === requestedCapabilityId);
  if (!match) {
    return {
      route_status: 'unresolved',
      reason_codes: ['runtime.route.capability_not_registered'],
    };
  }

  return buildResolvedRoute({ entry: match, requestedServiceObjectId });
}

function resolveByRequestedService({ entries, requestedServiceObjectId }) {
  if (!requestedServiceObjectId) {
    return null;
  }

  const match = entries.find((entry) => entry.supported_service_object_ids.includes(requestedServiceObjectId));
  if (!match) {
    return {
      route_status: 'unresolved',
      reason_codes: ['runtime.route.service_not_registered'],
    };
  }

  return buildResolvedRoute({ entry: match, requestedServiceObjectId });
}

function resolveByMatchTokens({ entries, userInputText, requestedServiceObjectId }) {
  const normalizedInput = normalizeMatchText(userInputText);
  if (!normalizedInput) {
    return null;
  }

  const tokens = splitInputTokens(userInputText);

  const match = entries.find((entry) => {
    if (!supportsMatchTokens(entry)) {
      return false;
    }

    if (entry.match_tokens.length === 0) {
      return false;
    }

    return entry.match_tokens.some((matchToken) => {
      if (tokens.includes(matchToken)) {
        return true;
      }
      return normalizedInput.includes(matchToken);
    });
  });

  if (!match) {
    return {
      route_status: 'unresolved',
      reason_codes: ['runtime.route.unresolved'],
    };
  }

  return buildResolvedRoute({ entry: match, requestedServiceObjectId });
}

function normalizeFallback(defaultFallback) {
  const fallbackCapabilityId = defaultFallback?.fallback_capability_id ?? 'navly.system.capability_explanation';
  const fallbackServiceObjectId = defaultFallback?.fallback_service_object_id ?? 'navly.service.system.capability_explanation';

  assertCapabilityId(fallbackCapabilityId);
  assertServiceObjectId(fallbackServiceObjectId);

  return {
    result_status: defaultFallback?.result_status ?? 'fallback',
    reason_code: defaultFallback?.reason_code ?? 'runtime.route.unresolved',
    next_action: defaultFallback?.next_action ?? 'request_capability_clarification',
    fallback_capability_id: fallbackCapabilityId,
    fallback_service_object_id: fallbackServiceObjectId,
  };
}

function chooseTargetScopeRef({ interactionContext }) {
  const grantedScopeRefs = interactionContext.access_context_envelope.granted_scope_refs;

  const hintedScope = interactionContext.target_scope_hint;
  if (hintedScope && grantedScopeRefs.includes(hintedScope)) {
    return assertScopeRef(hintedScope);
  }

  if (interactionContext.access_context_envelope.primary_scope_ref) {
    return assertScopeRef(interactionContext.access_context_envelope.primary_scope_ref);
  }

  if (grantedScopeRefs.length > 0) {
    return assertScopeRef(grantedScopeRefs[0]);
  }

  throw new Error('runtime.route.scope_unavailable');
}

export function loadCapabilityRouteRegistry(registryPath = defaultRegistryPath) {
  const cacheKey = path.resolve(registryPath);
  const cachedRegistry = capabilityRouteRegistryCache.get(cacheKey);
  if (cachedRegistry) {
    return cloneRegistry(cachedRegistry);
  }

  const rawRegistry = readJson(cacheKey);
  const entries = Array.isArray(rawRegistry.entries) ? rawRegistry.entries.map(normalizeEntry) : [];

  const normalizedRegistry = {
    registry_name: rawRegistry.registry_name,
    status: rawRegistry.status,
    route_strategy: rawRegistry.route_strategy,
    entries,
    default_fallback: normalizeFallback(rawRegistry.default_fallback),
  };

  capabilityRouteRegistryCache.set(cacheKey, normalizedRegistry);
  return cloneRegistry(normalizedRegistry);
}

export function clearCapabilityRouteRegistryCache(registryPath = null) {
  if (!registryPath) {
    capabilityRouteRegistryCache.clear();
    return;
  }

  capabilityRouteRegistryCache.delete(path.resolve(registryPath));
}

export function resolveCapabilityRoute({ interactionContext, routeRegistry = loadCapabilityRouteRegistry() }) {
  const activeEntries = routeRegistry.entries.filter((entry) => !String(entry.status ?? '').startsWith('retired'));

  if (activeEntries.length === 0) {
    return {
      route_status: 'unresolved',
      reason_codes: ['runtime.route.registry_empty'],
      fallback_plan: routeRegistry.default_fallback,
      selected_capability_id: routeRegistry.default_fallback.fallback_capability_id,
      selected_service_object_id: routeRegistry.default_fallback.fallback_service_object_id,
      route_id: null,
    };
  }

  const resolutionCandidates = [
    resolveByRequestedCapability({
      entries: activeEntries,
      requestedCapabilityId: interactionContext.requested_capability_id,
      requestedServiceObjectId: interactionContext.requested_service_object_id,
    }),
    resolveByRequestedService({
      entries: activeEntries,
      requestedServiceObjectId: interactionContext.requested_service_object_id,
    }),
    resolveByMatchTokens({
      entries: activeEntries,
      userInputText: interactionContext.user_input_text,
      requestedServiceObjectId: interactionContext.requested_service_object_id,
    }),
  ].filter(Boolean);

  const resolved = resolutionCandidates.find((candidate) => candidate.route_status === 'resolved');
  if (resolved) {
    return {
      ...resolved,
      reason_codes: normalizeReasonCodes(resolved.reason_codes, null),
      fallback_plan: null,
    };
  }

  const unresolvedReasonCodes = normalizeReasonCodes(
    resolutionCandidates.flatMap((candidate) => candidate.reason_codes ?? []),
    routeRegistry.default_fallback.reason_code,
  );

  return {
    route_status: 'unresolved',
    route_id: null,
    selected_capability_id: routeRegistry.default_fallback.fallback_capability_id,
    selected_service_object_id: routeRegistry.default_fallback.fallback_service_object_id,
    reason_codes: unresolvedReasonCodes,
    fallback_plan: routeRegistry.default_fallback,
  };
}

export function buildRuntimeExecutionPlan({ interactionContext, routeResult }) {
  if (routeResult.route_status !== 'resolved') {
    return null;
  }

  const targetScopeRef = chooseTargetScopeRef({ interactionContext });

  return {
    request_id: interactionContext.request_id,
    runtime_trace_ref: interactionContext.runtime_trace_ref,
    selected_capability_id: routeResult.selected_capability_id,
    selected_service_object_id: routeResult.selected_service_object_id,
    target_scope_ref: targetScopeRef,
    target_business_date: interactionContext.target_business_date_hint,
    freshness_mode: interactionContext.freshness_mode,
    include_explanation: true,
  };
}
