import fs from 'node:fs';
import path from 'node:path';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';

const moduleDir = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(moduleDir, '..', '..', '..');
const sharedContractsRoot = path.join(repoRoot, 'shared', 'contracts');

function loadSchema(relativePath) {
  return JSON.parse(fs.readFileSync(path.join(sharedContractsRoot, relativePath), 'utf8'));
}

function loadPattern(relativePath) {
  const schema = loadSchema(relativePath);
  if (!schema.pattern) {
    throw new Error(`shared schema ${relativePath} does not expose a pattern`);
  }
  return new RegExp(schema.pattern);
}

function loadPatternOrFallback(relativePath, fallbackPattern) {
  const schema = loadSchema(relativePath);
  if (schema.pattern) {
    return new RegExp(schema.pattern);
  }
  return fallbackPattern;
}

function loadEnum(relativePath) {
  const schema = loadSchema(relativePath);
  if (!Array.isArray(schema.enum)) {
    throw new Error(`shared schema ${relativePath} does not expose an enum`);
  }
  return [...schema.enum];
}

export const sharedPatterns = {
  capabilityId: loadPattern('capability/capability_id.schema.json'),
  serviceObjectId: loadPattern('service/service_object_id.schema.json'),
  traceRef: loadPattern('trace/trace_ref.schema.json'),
  stateTraceRef: loadPattern('trace/state_trace_ref.schema.json'),
  runTraceRef: loadPattern('trace/run_trace_ref.schema.json'),
  runtimeTraceRef: loadPatternOrFallback(
    'interaction/runtime_trace_ref.schema.json',
    /^navly:runtime-trace:[A-Za-z0-9._:-]+$/,
  ),
  decisionRef: loadPattern('access/decision_ref.schema.json'),
  scopeRef: loadPattern('access/scope_ref.schema.json'),
  actorRef: loadPattern('access/actor_ref.schema.json'),
  sessionRef: loadPattern('access/session_ref.schema.json'),
  conversationRef: loadPattern('access/conversation_ref.schema.json'),
  tenantRef: loadPattern('access/tenant_ref.schema.json'),
};

export const sharedEnums = {
  runtimeResultStatus: loadEnum('enums/runtime_result_status.schema.json'),
  accessDecisionStatus: loadEnum('enums/access_decision_status.schema.json'),
  readinessStatus: loadEnum('enums/readiness_status.schema.json'),
  serviceStatus: loadEnum('enums/service_status.schema.json'),
  freshnessMode: loadEnum('enums/freshness_mode.schema.json'),
};

function assertNonEmptyString(label, value) {
  if (typeof value !== 'string' || value.trim().length === 0) {
    throw new Error(`${label} must be a non-empty string`);
  }
  return value;
}

export function assertPattern(label, value, pattern) {
  assertNonEmptyString(label, value);
  if (!pattern.test(value)) {
    throw new Error(`${label} does not match shared contract pattern: ${value}`);
  }
  return value;
}

export function assertEnum(label, value, allowedValues) {
  if (!allowedValues.includes(value)) {
    throw new Error(`${label} must be one of ${allowedValues.join(', ')}, received ${value}`);
  }
  return value;
}

export function assertCapabilityId(value) {
  return assertPattern('capability_id', value, sharedPatterns.capabilityId);
}

export function assertServiceObjectId(value) {
  return assertPattern('service_object_id', value, sharedPatterns.serviceObjectId);
}

export function assertTraceRef(value) {
  return assertPattern('trace_ref', value, sharedPatterns.traceRef);
}

export function assertDecisionRef(value) {
  return assertPattern('decision_ref', value, sharedPatterns.decisionRef);
}

export function assertScopeRef(value) {
  return assertPattern('scope_ref', value, sharedPatterns.scopeRef);
}

export function stableHashId(...parts) {
  return createHash('sha256').update(parts.join('|')).digest('hex').slice(0, 16);
}

export function buildRuntimeTraceRef(requestId, traceRef) {
  return `navly:runtime-trace:${stableHashId(requestId, traceRef)}`;
}

export function asArray(label, value) {
  if (!Array.isArray(value)) {
    throw new Error(`${label} must be an array`);
  }
  return value;
}

export function validateAccessContextEnvelopeShape(accessContextEnvelope) {
  if (!accessContextEnvelope || typeof accessContextEnvelope !== 'object') {
    throw new Error('access_context_envelope must be an object');
  }

  assertNonEmptyString('request_id', accessContextEnvelope.request_id);
  assertTraceRef(accessContextEnvelope.trace_ref);
  assertDecisionRef(accessContextEnvelope.decision_ref);
  assertPattern('actor_ref', accessContextEnvelope.actor_ref, sharedPatterns.actorRef);
  assertPattern('session_ref', accessContextEnvelope.session_ref, sharedPatterns.sessionRef);
  assertPattern('conversation_ref', accessContextEnvelope.conversation_ref, sharedPatterns.conversationRef);
  assertPattern('tenant_ref', accessContextEnvelope.tenant_ref, sharedPatterns.tenantRef);
  assertScopeRef(accessContextEnvelope.primary_scope_ref);

  asArray('granted_scope_refs', accessContextEnvelope.granted_scope_refs).forEach((scopeRef, index) => {
    try {
      assertScopeRef(scopeRef);
    } catch (error) {
      throw new Error(`granted_scope_refs[${index}] invalid: ${error.message}`);
    }
  });

  asArray('granted_capability_ids', accessContextEnvelope.granted_capability_ids).forEach((capabilityId, index) => {
    try {
      assertCapabilityId(capabilityId);
    } catch (error) {
      throw new Error(`granted_capability_ids[${index}] invalid: ${error.message}`);
    }
  });

  assertNonEmptyString('issued_at', accessContextEnvelope.issued_at);
  assertNonEmptyString('expires_at', accessContextEnvelope.expires_at);

  return accessContextEnvelope;
}

export function validateAccessDecisionShape(accessDecision) {
  if (!accessDecision || typeof accessDecision !== 'object') {
    throw new Error('access_decision must be an object');
  }

  assertDecisionRef(accessDecision.decision_ref);
  assertNonEmptyString('request_id', accessDecision.request_id);
  assertTraceRef(accessDecision.trace_ref);
  assertEnum('decision_status', accessDecision.decision_status, sharedEnums.accessDecisionStatus);
  assertPattern('actor_ref', accessDecision.actor_ref, sharedPatterns.actorRef);
  assertPattern('session_ref', accessDecision.session_ref, sharedPatterns.sessionRef);
  assertCapabilityId(accessDecision.target_capability_id);
  assertScopeRef(accessDecision.target_scope_ref);
  asArray('reason_codes', accessDecision.reason_codes ?? []);
  asArray('restriction_codes', accessDecision.restriction_codes ?? []);
  asArray('obligation_codes', accessDecision.obligation_codes ?? []);
  assertNonEmptyString('decided_at', accessDecision.decided_at);
  assertNonEmptyString('expires_at', accessDecision.expires_at);

  return accessDecision;
}

export function validateReadinessResponseShape(readinessResponse) {
  if (!readinessResponse || typeof readinessResponse !== 'object') {
    throw new Error('capability_readiness_response must be an object');
  }

  assertNonEmptyString('request_id', readinessResponse.request_id);
  assertTraceRef(readinessResponse.trace_ref);
  assertCapabilityId(readinessResponse.capability_id);
  assertEnum('readiness_status', readinessResponse.readiness_status, sharedEnums.readinessStatus);
  assertScopeRef(readinessResponse.evaluated_scope_ref);
  assertNonEmptyString('requested_business_date', readinessResponse.requested_business_date);
  assertNonEmptyString('latest_usable_business_date', readinessResponse.latest_usable_business_date);
  asArray('reason_codes', readinessResponse.reason_codes);
  asArray('blocking_dependencies', readinessResponse.blocking_dependencies);
  asArray('state_trace_refs', readinessResponse.state_trace_refs);
  asArray('run_trace_refs', readinessResponse.run_trace_refs);
  assertNonEmptyString('evaluated_at', readinessResponse.evaluated_at);

  return readinessResponse;
}

export function validateThemeServiceResponseShape(serviceResponse) {
  if (!serviceResponse || typeof serviceResponse !== 'object') {
    throw new Error('theme_service_response must be an object');
  }

  assertNonEmptyString('request_id', serviceResponse.request_id);
  assertTraceRef(serviceResponse.trace_ref);
  assertCapabilityId(serviceResponse.capability_id);
  assertServiceObjectId(serviceResponse.service_object_id);
  assertEnum('service_status', serviceResponse.service_status, sharedEnums.serviceStatus);

  if (!serviceResponse.service_object || typeof serviceResponse.service_object !== 'object') {
    throw new Error('theme_service_response.service_object must be an object');
  }

  if (!serviceResponse.data_window || typeof serviceResponse.data_window !== 'object') {
    throw new Error('theme_service_response.data_window must be an object');
  }

  asArray('state_trace_refs', serviceResponse.state_trace_refs);
  asArray('run_trace_refs', serviceResponse.run_trace_refs);
  assertNonEmptyString('served_at', serviceResponse.served_at);

  return serviceResponse;
}

export function ensureRuntimeResultStatus(value) {
  return assertEnum('runtime_result_status', value, sharedEnums.runtimeResultStatus);
}

export function normalizeReasonCodes(reasonCodes, fallbackReasonCode) {
  const values = Array.isArray(reasonCodes) ? reasonCodes : [];
  const normalized = [...new Set(values.filter((code) => typeof code === 'string' && code.trim().length > 0))];
  if (normalized.length > 0) {
    return normalized;
  }
  return fallbackReasonCode ? [fallbackReasonCode] : [];
}

export function mergeTraceRefs(...traceRefCollections) {
  const merged = [];
  for (const collection of traceRefCollections) {
    if (!Array.isArray(collection)) {
      continue;
    }
    for (const ref of collection) {
      if (typeof ref !== 'string' || ref.trim().length === 0) {
        continue;
      }
      if (!merged.includes(ref)) {
        merged.push(ref);
      }
    }
  }
  return merged;
}

export function isTraceFamilyRef(value) {
  if (typeof value !== 'string' || value.trim().length === 0) {
    return false;
  }

  const allowedPatterns = [
    sharedPatterns.traceRef,
    sharedPatterns.stateTraceRef,
    sharedPatterns.runTraceRef,
    sharedPatterns.runtimeTraceRef,
  ];

  return allowedPatterns.some((pattern) => pattern.test(value));
}

export function filterTraceRefsByFamily(...traceRefCollections) {
  return mergeTraceRefs(...traceRefCollections).filter((ref) => isTraceFamilyRef(ref));
}

export function todayIsoDate(now = new Date().toISOString()) {
  return now.slice(0, 10);
}
