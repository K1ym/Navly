import {
  assertCapabilityId,
  assertServiceObjectId,
  ensureObject,
  uniqueStrings,
} from '../adapters/openclaw/bridge-shared-alignment.mjs';
import { buildRuntimeRequestEnvelope } from './runtime-request-envelope-backbone.mjs';

function normalizePublicationEntry(publicationEntry) {
  const entry = ensureObject('publicationEntry', publicationEntry);
  assertCapabilityId(entry.capability_id);
  assertServiceObjectId(entry.service_object_id);

  const supportedServiceObjectIds = uniqueStrings([
    entry.service_object_id,
    ...(Array.isArray(entry.supported_service_object_ids) ? entry.supported_service_object_ids : []),
  ]);
  supportedServiceObjectIds.forEach((value) => assertServiceObjectId(value));

  return {
    ...entry,
    supported_service_object_ids: supportedServiceObjectIds,
  };
}

export function buildPublishedToolRuntimeRequestEnvelope({
  hostIngressEnvelope,
  gate0Enforcement,
  authorizedSessionLink,
  accessContextEnvelope,
  publicationEntry,
  requestedServiceObjectId = null,
}) {
  const ingress = ensureObject('hostIngressEnvelope', hostIngressEnvelope);
  const entry = normalizePublicationEntry(publicationEntry);
  const selectedServiceObjectId = requestedServiceObjectId ?? entry.service_object_id;
  if (!entry.supported_service_object_ids.includes(selectedServiceObjectId)) {
    return null;
  }

  if (ingress.requested_capability_id && ingress.requested_capability_id !== entry.capability_id) {
    return null;
  }
  if (ingress.requested_service_object_id && ingress.requested_service_object_id !== selectedServiceObjectId) {
    return null;
  }

  return buildRuntimeRequestEnvelope({
    hostIngressEnvelope: {
      ...ingress,
      requested_capability_id: entry.capability_id,
      requested_service_object_id: selectedServiceObjectId,
      structured_input_slots: {
        ...(ingress.structured_input_slots ?? {}),
        publication_tool_name: entry.tool_name,
        publication_visibility_scope: entry.visibility_scope,
        publication_version: entry.publication_version ?? null,
      },
    },
    gate0Enforcement,
    authorizedSessionLink,
    accessContextEnvelope,
  });
}
