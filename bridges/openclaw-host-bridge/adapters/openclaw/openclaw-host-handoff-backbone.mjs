import { normalizeOpenClawHostIngress } from '../../ingress/host-ingress-normalizer.mjs';
import { assembleIngressIdentityEnvelope } from '../../auth-linkage/ingress-identity-envelope-backbone.mjs';
import { enforceGate0Result } from '../../auth-linkage/gate0-enforcement-backbone.mjs';
import { buildAuthorizedSessionLink } from '../../auth-linkage/authorized-session-link-backbone.mjs';
import { buildRuntimeRequestEnvelope } from '../../runtime-handoff/runtime-request-envelope-backbone.mjs';
import { buildHostDispatchResult } from '../../dispatch/host-dispatch-handoff-backbone.mjs';
import { createMilestoneBTraceBundle } from '../../diagnostics/host-trace-backbone.mjs';

export function runOpenClawHostMilestoneBBackbone({
  rawHostIngress,
  gate0Result,
  accessContextEnvelope = null,
  runtimeResultEnvelope = null,
  now = new Date().toISOString(),
}) {
  const hostIngressEnvelope = normalizeOpenClawHostIngress({ rawHostIngress, now });
  const ingressIdentityEnvelope = assembleIngressIdentityEnvelope({ hostIngressEnvelope });
  const gate0Enforcement = enforceGate0Result({
    hostIngressEnvelope,
    gate0Result,
    accessContextEnvelope,
    now,
  });
  const authorizedSessionLink = buildAuthorizedSessionLink({
    hostIngressEnvelope,
    gate0Enforcement,
    accessContextEnvelope,
    now,
  });
  const runtimeRequestEnvelope = buildRuntimeRequestEnvelope({
    hostIngressEnvelope,
    gate0Enforcement,
    authorizedSessionLink,
    accessContextEnvelope,
  });
  const hostDispatchResult = buildHostDispatchResult({
    hostIngressEnvelope,
    gate0Enforcement,
    authorizedSessionLink,
    runtimeRequestEnvelope,
    runtimeResultEnvelope,
    now,
  });
  const hostTraceEvents = createMilestoneBTraceBundle({
    hostIngressEnvelope,
    ingressIdentityEnvelope,
    gate0Enforcement,
    authorizedSessionLink,
    runtimeRequestEnvelope,
    hostDispatchResult,
    runtimeResultEnvelope,
    now,
  });

  return {
    host_ingress_envelope: hostIngressEnvelope,
    ingress_identity_envelope: ingressIdentityEnvelope,
    gate0_enforcement: gate0Enforcement,
    authorized_session_link: authorizedSessionLink,
    runtime_request_envelope: runtimeRequestEnvelope,
    host_dispatch_result: hostDispatchResult,
    host_trace_events: hostTraceEvents,
  };
}
