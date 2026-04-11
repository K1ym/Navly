import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import test from 'node:test';
import assert from 'node:assert/strict';

import {
  buildCapabilityToolPublicationManifest,
  buildCapabilityToolPublicationRefresh,
} from '../tool-publication/capability-tool-publication-backbone.mjs';

function writeJson(filePath, payload) {
  fs.writeFileSync(filePath, `${JSON.stringify(payload, null, 2)}\n`, 'utf8');
}

test('tool publication manifest respects the registry default binding when multiple bindings exist', () => {
  const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'navly-tool-publication-'));
  const capabilityRegistryPath = path.join(tempDir, 'capability-registry.seed.json');
  const serviceBindingsPath = path.join(tempDir, 'capability-service-bindings.seed.json');

  writeJson(capabilityRegistryPath, {
    registry_name: 'capability_registry',
    entries: [
      {
        capability_id: 'navly.store.daily_overview',
        default_service_object_id: 'navly.service.store.daily_overview',
        status: 'owner_surface_published',
      },
    ],
  });

  writeJson(serviceBindingsPath, {
    registry_name: 'capability_service_binding_registry',
    entries: [
      {
        capability_id: 'navly.store.daily_overview',
        service_object_id: 'navly.service.store.daily_overview.experimental',
        status: 'owner_surface_published',
        is_default_binding: false,
        include_explanation_supported: false,
      },
      {
        capability_id: 'navly.store.daily_overview',
        service_object_id: 'navly.service.store.daily_overview',
        status: 'owner_surface_published',
        is_default_binding: true,
        include_explanation_supported: true,
      },
    ],
  });

  const manifest = buildCapabilityToolPublicationManifest({
    capabilityRegistryPath,
    serviceBindingsPath,
    publicationVersion: 'test-publication-v1',
    now: '2026-04-10T19:00:00.000Z',
  });

  const dailyOverviewTool = manifest.tools.find((entry) => entry.capability_id === 'navly.store.daily_overview');
  assert.ok(dailyOverviewTool);
  assert.equal(dailyOverviewTool.service_object_id, 'navly.service.store.daily_overview');
  assert.deepEqual(dailyOverviewTool.supported_service_object_ids, [
    'navly.service.store.daily_overview',
    'navly.service.system.capability_explanation',
  ]);
});

test('tool publication manifest fails closed when no default binding can be resolved', () => {
  const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'navly-tool-publication-'));
  const capabilityRegistryPath = path.join(tempDir, 'capability-registry.seed.json');
  const serviceBindingsPath = path.join(tempDir, 'capability-service-bindings.seed.json');

  writeJson(capabilityRegistryPath, {
    registry_name: 'capability_registry',
    entries: [
      {
        capability_id: 'navly.store.staff_board',
        default_service_object_id: 'navly.service.store.staff_board',
        status: 'owner_surface_published',
      },
    ],
  });

  writeJson(serviceBindingsPath, {
    registry_name: 'capability_service_binding_registry',
    entries: [
      {
        capability_id: 'navly.store.staff_board',
        service_object_id: 'navly.service.store.staff_board.experimental_a',
        status: 'owner_surface_published',
        is_default_binding: false,
        include_explanation_supported: true,
      },
      {
        capability_id: 'navly.store.staff_board',
        service_object_id: 'navly.service.store.staff_board.experimental_b',
        status: 'owner_surface_published',
        is_default_binding: false,
        include_explanation_supported: true,
      },
    ],
  });

  assert.throws(
    () => buildCapabilityToolPublicationManifest({
      capabilityRegistryPath,
      serviceBindingsPath,
      publicationVersion: 'test-publication-v1',
    }),
    /default binding missing for capability navly\.store\.staff_board/,
  );
});

test('tool publication refresh ignores property-order-only differences', () => {
  const previousManifest = {
    publication_version: 'phase-1-capability-publication-v1',
    tools: [
      {
        tool_name: 'navly_store_daily_overview',
        capability_id: 'navly.store.daily_overview',
        service_object_id: 'navly.service.store.daily_overview',
        supported_service_object_ids: [
          'navly.service.store.daily_overview',
          'navly.service.system.capability_explanation',
        ],
        visibility_scope: 'host_visible',
        owner_module: 'runtime',
        publication_kind: 'capability_tool',
        tool_description: 'Capability-first host tool for navly.store.daily_overview.',
        input_schema_ref: 'shared/contracts/interaction/runtime_request_envelope.schema.json',
        output_schema_ref: 'shared/contracts/interaction/runtime_result_envelope.schema.json',
        publication_version: 'phase-1-capability-publication-v1',
      },
    ],
  };

  const nextManifest = {
    publication_version: 'phase-1-capability-publication-v1',
    tools: [
      {
        capability_id: 'navly.store.daily_overview',
        tool_name: 'navly_store_daily_overview',
        supported_service_object_ids: [
          'navly.service.store.daily_overview',
          'navly.service.system.capability_explanation',
        ],
        service_object_id: 'navly.service.store.daily_overview',
        publication_kind: 'capability_tool',
        owner_module: 'runtime',
        visibility_scope: 'host_visible',
        tool_description: 'Capability-first host tool for navly.store.daily_overview.',
        output_schema_ref: 'shared/contracts/interaction/runtime_result_envelope.schema.json',
        input_schema_ref: 'shared/contracts/interaction/runtime_request_envelope.schema.json',
        publication_version: 'phase-1-capability-publication-v1',
      },
    ],
  };

  const refreshResult = buildCapabilityToolPublicationRefresh({
    previousManifest,
    nextManifest,
    now: '2026-04-10T19:00:00.000Z',
  });

  assert.deepEqual(refreshResult.changed_tool_names, []);
});
