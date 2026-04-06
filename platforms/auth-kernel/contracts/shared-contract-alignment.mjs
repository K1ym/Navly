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
  traceRef: loadPattern('trace/trace_ref.schema.json'),
};

export const sharedEnums = {
  accessDecisionStatus: loadEnum('enums/access_decision_status.schema.json'),
  scopeKind: loadEnum('enums/scope_kind.schema.json'),
};

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
  return createHash('sha256').update(parts.join('|')).digest('hex').slice(0, 16);
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

export function buildActorRef(actorId) {
  return assertMatchesSharedPattern(
    'actor_ref',
    `navly:actor:${sanitizeRefSegment(actorId)}`,
    sharedPatterns.actorRef,
  );
}

export function buildSessionRef(sessionId) {
  return assertMatchesSharedPattern(
    'session_ref',
    `navly:session:${sanitizeRefSegment(sessionId)}`,
    sharedPatterns.sessionRef,
  );
}

export function buildDecisionRef(decisionId) {
  return assertMatchesSharedPattern(
    'decision_ref',
    `navly:decision:${sanitizeRefSegment(decisionId)}`,
    sharedPatterns.decisionRef,
  );
}

export function buildConversationRef(conversationId) {
  return assertMatchesSharedPattern(
    'conversation_ref',
    `navly:conversation:${sanitizeRefSegment(conversationId)}`,
    sharedPatterns.conversationRef,
  );
}

export function buildScopeRef(scopeKind, scopeId) {
  return assertMatchesSharedPattern(
    'scope_ref',
    `navly:scope:${sanitizeRefSegment(scopeKind)}:${sanitizeRefSegment(scopeId)}`,
    sharedPatterns.scopeRef,
  );
}

export function buildTenantRef(tenantId) {
  return assertMatchesSharedPattern(
    'tenant_ref',
    `navly:tenant:${sanitizeRefSegment(tenantId)}`,
    sharedPatterns.tenantRef,
  );
}

export function buildTraceRef(traceId) {
  return assertMatchesSharedPattern(
    'trace_ref',
    `navly:trace:${sanitizeRefSegment(traceId)}`,
    sharedPatterns.traceRef,
  );
}

export function assertCapabilityId(capabilityId) {
  return assertMatchesSharedPattern('capability_id', capabilityId, sharedPatterns.capabilityId);
}

export function ensureArrayOfSharedPattern(label, values, pattern) {
  if (!Array.isArray(values)) {
    throw new Error(`${label} must be an array`);
  }
  values.forEach((value, index) => assertMatchesSharedPattern(`${label}[${index}]`, value, pattern));
  return values;
}

export function validateAccessDecisionShape(accessDecision) {
  if (!accessDecision || typeof accessDecision !== 'object') {
    throw new Error('access_decision must be an object');
  }

  assertMatchesSharedPattern('decision_ref', accessDecision.decision_ref, sharedPatterns.decisionRef);
  assertSharedEnumValue('decision_status', accessDecision.decision_status, sharedEnums.accessDecisionStatus);
  assertMatchesSharedPattern('actor_ref', accessDecision.actor_ref, sharedPatterns.actorRef);
  assertMatchesSharedPattern('session_ref', accessDecision.session_ref, sharedPatterns.sessionRef);
  assertMatchesSharedPattern('target_scope_ref', accessDecision.target_scope_ref, sharedPatterns.scopeRef);
  assertCapabilityId(accessDecision.target_capability_id);
  assertMatchesSharedPattern('trace_ref', accessDecision.trace_ref, sharedPatterns.traceRef);

  return accessDecision;
}

export function validateAccessContextEnvelopeShape(accessContextEnvelope) {
  if (!accessContextEnvelope || typeof accessContextEnvelope !== 'object') {
    throw new Error('access_context_envelope must be an object');
  }

  assertMatchesSharedPattern('trace_ref', accessContextEnvelope.trace_ref, sharedPatterns.traceRef);
  assertMatchesSharedPattern('decision_ref', accessContextEnvelope.decision_ref, sharedPatterns.decisionRef);
  assertMatchesSharedPattern('actor_ref', accessContextEnvelope.actor_ref, sharedPatterns.actorRef);
  assertMatchesSharedPattern('session_ref', accessContextEnvelope.session_ref, sharedPatterns.sessionRef);
  assertMatchesSharedPattern('conversation_ref', accessContextEnvelope.conversation_ref, sharedPatterns.conversationRef);
  assertMatchesSharedPattern('tenant_ref', accessContextEnvelope.tenant_ref, sharedPatterns.tenantRef);
  assertMatchesSharedPattern('primary_scope_ref', accessContextEnvelope.primary_scope_ref, sharedPatterns.scopeRef);
  ensureArrayOfSharedPattern('granted_scope_refs', accessContextEnvelope.granted_scope_refs, sharedPatterns.scopeRef);

  if (!Array.isArray(accessContextEnvelope.granted_capability_ids)) {
    throw new Error('granted_capability_ids must be an array');
  }
  accessContextEnvelope.granted_capability_ids.forEach(assertCapabilityId);

  return accessContextEnvelope;
}

export function buildDeterministicId(prefix, ...parts) {
  return `${prefix}-${stableHashId(...parts)}`;
}
