import fs from 'node:fs';
import path from 'node:path';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';

const moduleDir = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(moduleDir, '..', '..', '..', '..');
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
  actorRef: loadPattern('access/actor_ref.schema.json'),
  sessionRef: loadPattern('access/session_ref.schema.json'),
  decisionRef: loadPattern('access/decision_ref.schema.json'),
  scopeRef: loadPattern('access/scope_ref.schema.json'),
  conversationRef: loadPattern('access/conversation_ref.schema.json'),
  tenantRef: loadPattern('access/tenant_ref.schema.json'),
  capabilityId: loadPattern('capability/capability_id.schema.json'),
  serviceObjectId: loadPattern('service/service_object_id.schema.json'),
  traceRef: loadPattern('trace/trace_ref.schema.json'),
  stateTraceRef: loadPattern('trace/state_trace_ref.schema.json'),
  runTraceRef: loadPattern('trace/run_trace_ref.schema.json'),
  runtimeTraceRef: loadPatternOrFallback(
    'interaction/runtime_trace_ref.schema.json',
    /^navly:runtime-trace:[A-Za-z0-9._:-]+$/,
  ),
};

export const sharedEnums = {
  accessDecisionStatus: loadEnum('enums/access_decision_status.schema.json'),
  runtimeResultStatus: loadEnum('enums/runtime_result_status.schema.json'),
};

export function normalizeOptionalString(value) {
  if (value === undefined || value === null) {
    return null;
  }
  const trimmed = String(value).trim();
  return trimmed ? trimmed : null;
}

export function ensureObject(label, value) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    throw new Error(`${label} must be an object`);
  }
  return value;
}

export function asArray(value) {
  if (Array.isArray(value)) {
    return value;
  }
  if (value === undefined || value === null) {
    return [];
  }
  return [value];
}

export function uniqueStrings(values) {
  return [...new Set(asArray(values).filter((value) => typeof value === 'string' && value.trim()).map((value) => value.trim()))];
}

export function sanitizeRefSegment(value) {
  const sanitized = String(value ?? '')
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9._:-]+/g, '-')
    .replace(/^-+|-+$/g, '');

  if (!sanitized) {
    throw new Error('cannot build canonical ref from empty value');
  }

  return sanitized;
}

export function stableHashId(...parts) {
  return createHash('sha256').update(parts.map((part) => String(part ?? '')).join('|')).digest('hex').slice(0, 16);
}

export function buildDeterministicId(prefix, ...parts) {
  return `${prefix}-${stableHashId(...parts)}`;
}

export function assertMatchesSharedPattern(label, value, pattern) {
  if (typeof value !== 'string' || !pattern.test(value)) {
    throw new Error(`${label} does not match shared contract pattern: ${value}`);
  }
  return value;
}

export function assertSharedEnumValue(label, value, allowedValues) {
  if (!allowedValues.includes(value)) {
    throw new Error(`${label} must be one of ${allowedValues.join(', ')}, received ${value}`);
  }
  return value;
}

export function assertCapabilityId(capabilityId) {
  return assertMatchesSharedPattern('capability_id', capabilityId, sharedPatterns.capabilityId);
}

export function assertServiceObjectId(serviceObjectId) {
  return assertMatchesSharedPattern('service_object_id', serviceObjectId, sharedPatterns.serviceObjectId);
}

export function buildTraceRef(traceId) {
  return assertMatchesSharedPattern(
    'trace_ref',
    `navly:trace:${sanitizeRefSegment(traceId)}`,
    sharedPatterns.traceRef,
  );
}

export function buildIngressRef(...parts) {
  return `navly:ingress:${sanitizeRefSegment(buildDeterministicId('ingress', ...parts))}`;
}

export function buildHostLocalRef(kind, ...parts) {
  return `openclaw-host-bridge:${sanitizeRefSegment(kind)}:${sanitizeRefSegment(buildDeterministicId(kind, ...parts))}`;
}

export function normalizeDecisionStatus(gate0Result) {
  const status = gate0Result?.decision_status ?? gate0Result?.gate_status;
  return assertSharedEnumValue('gate0 decision status', status, sharedEnums.accessDecisionStatus);
}

export function validateAccessContextEnvelopeShape(accessContextEnvelope) {
  ensureObject('access_context_envelope', accessContextEnvelope);
  assertMatchesSharedPattern('trace_ref', accessContextEnvelope.trace_ref, sharedPatterns.traceRef);
  assertMatchesSharedPattern('decision_ref', accessContextEnvelope.decision_ref, sharedPatterns.decisionRef);
  assertMatchesSharedPattern('actor_ref', accessContextEnvelope.actor_ref, sharedPatterns.actorRef);
  assertMatchesSharedPattern('session_ref', accessContextEnvelope.session_ref, sharedPatterns.sessionRef);
  assertMatchesSharedPattern('conversation_ref', accessContextEnvelope.conversation_ref, sharedPatterns.conversationRef);
  assertMatchesSharedPattern('tenant_ref', accessContextEnvelope.tenant_ref, sharedPatterns.tenantRef);
  assertMatchesSharedPattern('primary_scope_ref', accessContextEnvelope.primary_scope_ref, sharedPatterns.scopeRef);

  if (!Array.isArray(accessContextEnvelope.granted_scope_refs) || !accessContextEnvelope.granted_scope_refs.length) {
    throw new Error('access_context_envelope.granted_scope_refs must be a non-empty array');
  }
  for (const scopeRef of accessContextEnvelope.granted_scope_refs) {
    assertMatchesSharedPattern('granted_scope_ref', scopeRef, sharedPatterns.scopeRef);
  }

  if (!Array.isArray(accessContextEnvelope.granted_capability_ids)) {
    throw new Error('access_context_envelope.granted_capability_ids must be an array');
  }
  for (const capabilityId of accessContextEnvelope.granted_capability_ids) {
    assertCapabilityId(capabilityId);
  }

  return accessContextEnvelope;
}

export function validateRuntimeRequestEnvelopeShape(runtimeRequestEnvelope) {
  ensureObject('runtime_request_envelope', runtimeRequestEnvelope);
  if (!runtimeRequestEnvelope.request_id || !runtimeRequestEnvelope.ingress_ref) {
    throw new Error('runtime_request_envelope must include request_id and ingress_ref');
  }
  assertMatchesSharedPattern('trace_ref', runtimeRequestEnvelope.trace_ref, sharedPatterns.traceRef);
  assertMatchesSharedPattern('decision_ref', runtimeRequestEnvelope.decision_ref, sharedPatterns.decisionRef);

  if (runtimeRequestEnvelope.requested_capability_id) {
    assertCapabilityId(runtimeRequestEnvelope.requested_capability_id);
  }
  if (runtimeRequestEnvelope.requested_service_object_id) {
    assertServiceObjectId(runtimeRequestEnvelope.requested_service_object_id);
  }

  validateAccessContextEnvelopeShape(runtimeRequestEnvelope.access_context_envelope);
  return runtimeRequestEnvelope;
}

export function validateLinkedTraceRef(label, value) {
  if (typeof value !== 'string') {
    throw new Error(`${label} must be a string trace ref`);
  }

  const allowedPatterns = [
    sharedPatterns.traceRef,
    sharedPatterns.stateTraceRef,
    sharedPatterns.runTraceRef,
    sharedPatterns.runtimeTraceRef,
  ];

  if (!allowedPatterns.some((pattern) => pattern.test(value))) {
    throw new Error(`${label} must match an allowed trace family pattern: ${value}`);
  }

  return value;
}

export function validateRuntimeResultEnvelopeShape(runtimeResultEnvelope) {
  ensureObject('runtime_result_envelope', runtimeResultEnvelope);
  if (!runtimeResultEnvelope.request_id || !runtimeResultEnvelope.runtime_trace_ref) {
    throw new Error('runtime_result_envelope must include request_id and runtime_trace_ref');
  }
  assertMatchesSharedPattern('runtime_trace_ref', runtimeResultEnvelope.runtime_trace_ref, sharedPatterns.runtimeTraceRef);

  assertSharedEnumValue('runtime_result_envelope.result_status', runtimeResultEnvelope.result_status, sharedEnums.runtimeResultStatus);
  assertCapabilityId(runtimeResultEnvelope.selected_capability_id);

  if (!Array.isArray(runtimeResultEnvelope.answer_fragments)) {
    throw new Error('runtime_result_envelope.answer_fragments must be an array');
  }
  if (!Array.isArray(runtimeResultEnvelope.reason_codes)) {
    throw new Error('runtime_result_envelope.reason_codes must be an array');
  }
  if (!Array.isArray(runtimeResultEnvelope.trace_refs)) {
    throw new Error('runtime_result_envelope.trace_refs must be an array');
  }
  runtimeResultEnvelope.trace_refs.forEach((traceRef, index) => {
    validateLinkedTraceRef(`runtime_result_envelope.trace_refs[${index}]`, traceRef);
  });

  return runtimeResultEnvelope;
}
