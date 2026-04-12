import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { definePluginEntry } from 'openclaw/plugin-sdk/core';

import { createNavlyFirstPartyToolFactory } from './runtime.mjs';

const moduleDir = path.dirname(fileURLToPath(import.meta.url));

const ALL_TOOL_NAMES = [
  'navly_daily_overview',
  'navly_member_insight',
  'navly_finance_summary',
  'navly_staff_board',
  'navly_explain_unavailable',
  'navly_sync_status',
  'navly_backfill_status',
  'navly_rerun_sync',
  'navly_trigger_backfill',
  'navly_quality_report',
];

export default definePluginEntry({
  id: 'navly-first-party-host',
  name: 'Navly First-Party Host',
  description: 'Publishes Navly first-party capability tools and bundled skills into live OpenClaw profiles.',
  register(api) {
    api.registerTool(
      createNavlyFirstPartyToolFactory({
        pluginConfig: api.pluginConfig ?? {},
        moduleDir,
      }),
      { names: ALL_TOOL_NAMES },
    );
  },
});
