import test from 'node:test';
import assert from 'node:assert/strict';

import {
  buildFirstPartyToolPublicationManifest,
  discoverFirstPartyHostSurface,
  readCommittedFirstPartyToolPublicationManifest,
} from '../tool-publication/first-party-host-surface.mjs';

test('first-party host surface publishes the closeout skill list, tool list, and committed manifest', () => {
  const surface = discoverFirstPartyHostSurface();
  const manifest = buildFirstPartyToolPublicationManifest();
  const committedManifest = readCommittedFirstPartyToolPublicationManifest();

  assert.equal(surface.skill_count, 7);
  assert.equal(surface.tool_count, 10);
  assert.equal(manifest.skill_count, 7);
  assert.equal(manifest.tool_count, 10);

  const syncOpsSkill = manifest.skills.find((skill) => skill.skill_id === 'navly-sync-ops');
  assert.deepEqual(syncOpsSkill.tool_names, [
    'navly_sync_status',
    'navly_backfill_status',
    'navly_rerun_sync',
    'navly_trigger_backfill',
  ]);

  const managerTools = manifest.tools.filter((tool) => tool.host_agent_id === 'main');
  assert.deepEqual(
    managerTools.map((tool) => tool.tool_name),
    [
      'navly_daily_overview',
      'navly_member_insight',
      'navly_finance_summary',
      'navly_staff_board',
      'navly_explain_unavailable',
    ],
  );

  assert.ok(manifest.tools.every((tool) => tool.required_context_fields.includes('access_context_envelope')));
  assert.ok(manifest.tools.every((tool) => tool.required_context_fields.includes('decision_ref')));
  assert.ok(manifest.tools.every((tool) => tool.runtime_handoff.requested_capability_id === tool.capability_id));
  assert.ok(manifest.tools.every((tool) => tool.runtime_handoff.requested_service_object_id === tool.service_object_id));
  assert.ok(
    manifest.tools.every((tool) => !/(Get[A-Z]|qinqin|sql|table)/i.test(tool.tool_name)),
    'host-visible tools must stay capability-oriented',
  );

  assert.deepEqual(committedManifest, manifest);
});

