import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

import { resolveActorFromIngress } from '../actor-registry/actor-resolution-backbone.mjs';
import { buildBindingSnapshot } from '../bindings/binding-backbone.mjs';

function withOverrideDir(files, callback) {
  const previous = process.env.NAVLY_AUTH_KERNEL_OVERRIDE_DIR;
  const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'navly-auth-override-'));
  try {
    for (const [fileName, payload] of Object.entries(files)) {
      fs.writeFileSync(path.join(tempDir, fileName), JSON.stringify(payload, null, 2));
    }
    process.env.NAVLY_AUTH_KERNEL_OVERRIDE_DIR = tempDir;
    return callback();
  } finally {
    if (previous === undefined) {
      delete process.env.NAVLY_AUTH_KERNEL_OVERRIDE_DIR;
    } else {
      process.env.NAVLY_AUTH_KERNEL_OVERRIDE_DIR = previous;
    }
    fs.rmSync(tempDir, { recursive: true, force: true });
  }
}

function ingressEvidence(aliasValue, targetScopeHint = null) {
  return {
    request_id: 'req-auth-override-001',
    trace_ref: 'navly:trace:req-auth-override-001',
    channel_kind: 'wecom',
    message_mode: 'direct_message',
    host_session_ref: 'openclaw:session:main:wecom:direct:test-user',
    host_workspace_ref: 'openclaw:workspace:main',
    host_conversation_ref: 'openclaw:conversation:direct:test-user',
    host_message_ref: 'openclaw:message:test-001',
    peer_identity_evidence: [
      {
        alias_namespace: 'wecom_user_id',
        alias_value: aliasValue,
      },
    ],
    message_text: '测试',
    target_scope_hint: targetScopeHint,
  };
}

test('actor registry override resolves a real wecom sender id', () => {
  withOverrideDir(
    {
      'actor-registry.override.json': {
        actors: [
          {
            actor_ref: 'navly:actor:wecom-niuxiaokai',
            actor_type: 'human_user',
            lifecycle_state: 'active',
            tenant_ref: 'navly:tenant:hetang-yuese',
            display_name: 'NiuXiaoKai',
          },
        ],
      },
      'identity-alias-registry.override.json': {
        aliases: [
          {
            alias_namespace: 'wecom_user_id',
            alias_value: 'NiuXiaoKai',
            actor_ref: 'navly:actor:wecom-niuxiaokai',
          },
        ],
      },
    },
    () => {
      const result = resolveActorFromIngress({
        ingressEvidence: ingressEvidence('NiuXiaoKai'),
      });

      assert.equal(result.resolution_status, 'resolved');
      assert.equal(result.actor_ref, 'navly:actor:wecom-niuxiaokai');
      assert.equal(result.tenant_ref, 'navly:tenant:hetang-yuese');
    },
  );
});

test('binding override supports real multi-store mapping while remaining bound through a default scope hint', () => {
  withOverrideDir(
    {
      'actor-registry.override.json': {
        actors: [
          {
            actor_ref: 'navly:actor:wecom-niuxiaokai',
            actor_type: 'human_user',
            lifecycle_state: 'active',
            tenant_ref: 'navly:tenant:hetang-yuese',
            display_name: 'NiuXiaoKai',
          },
        ],
      },
      'identity-alias-registry.override.json': {
        aliases: [
          {
            alias_namespace: 'wecom_user_id',
            alias_value: 'NiuXiaoKai',
            actor_ref: 'navly:actor:wecom-niuxiaokai',
          },
        ],
      },
      'role-binding.override.json': {
        bindings: [
          {
            actor_ref: 'navly:actor:wecom-niuxiaokai',
            role_id: 'navly.role.store_manager',
          },
        ],
      },
      'scope-binding.override.json': {
        bindings: [
          {
            actor_ref: 'navly:actor:wecom-niuxiaokai',
            tenant_ref: 'navly:tenant:hetang-yuese',
            scope_ref: 'navly:scope:store:627149864218629',
            is_primary: true,
          },
          {
            actor_ref: 'navly:actor:wecom-niuxiaokai',
            tenant_ref: 'navly:tenant:hetang-yuese',
            scope_ref: 'navly:scope:store:627150985244677',
            is_primary: false,
          },
        ],
      },
    },
    () => {
      const actorResolutionResult = resolveActorFromIngress({
        ingressEvidence: ingressEvidence('NiuXiaoKai'),
      });
      const bindingSnapshot = buildBindingSnapshot({
        ingressEvidence: ingressEvidence('NiuXiaoKai', 'navly:scope:store:627149864218629'),
        actorResolutionResult,
      });

      assert.equal(bindingSnapshot.actor_ref, 'navly:actor:wecom-niuxiaokai');
      assert.deepEqual(bindingSnapshot.role_ids, ['navly.role.store_manager']);
      assert.deepEqual(bindingSnapshot.granted_scope_refs, [
        'navly:scope:store:627149864218629',
        'navly:scope:store:627150985244677',
      ]);
      assert.equal(bindingSnapshot.selected_scope_ref, 'navly:scope:store:627149864218629');
      assert.equal(bindingSnapshot.conversation_binding_status, 'bound');
    },
  );
});
