from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable, Sequence

from backbone_support.postgres_truth_substrate import PostgresTruthSubstrate, utcnow_iso
from directory.nightly_sync_policy_registry import (
    resolve_nightly_sync_history_start_business_date,
    should_default_operator_backfill_to_full_history,
)
from ingestion.member_insight_vertical_slice import SOURCE_SYSTEM_ID
from workflows.postgres_temporal_nightly_sync import (
    NightlyPlannerPolicy,
    NightlySyncPlanner,
    NightlySyncRuntime,
    TemporalNightlySyncPlane,
    TemporalWorkerBootstrap,
)

SYNC_STATUS_CAPABILITY_ID = 'navly.ops.sync_status'
BACKFILL_STATUS_CAPABILITY_ID = 'navly.ops.backfill_status'
SYNC_RERUN_CAPABILITY_ID = 'navly.ops.sync_rerun'
SYNC_BACKFILL_CAPABILITY_ID = 'navly.ops.sync_backfill'
QUALITY_REPORT_CAPABILITY_ID = 'navly.ops.quality_report'

SYNC_STATUS_SERVICE_OBJECT_ID = 'navly.service.ops.sync_status'
BACKFILL_STATUS_SERVICE_OBJECT_ID = 'navly.service.ops.backfill_status'
SYNC_RERUN_SERVICE_OBJECT_ID = 'navly.service.ops.sync_rerun'
SYNC_BACKFILL_SERVICE_OBJECT_ID = 'navly.service.ops.sync_backfill'
QUALITY_REPORT_SERVICE_OBJECT_ID = 'navly.service.ops.quality_report'

READ_ONLY_OPERATOR_CAPABILITIES = frozenset({
    SYNC_STATUS_CAPABILITY_ID,
    BACKFILL_STATUS_CAPABILITY_ID,
    QUALITY_REPORT_CAPABILITY_ID,
})

ACTION_OPERATOR_CAPABILITIES = frozenset({
    SYNC_RERUN_CAPABILITY_ID,
    SYNC_BACKFILL_CAPABILITY_ID,
})

SUPPORTED_OPERATOR_SERVICE_OBJECT_IDS = {
    SYNC_STATUS_CAPABILITY_ID: SYNC_STATUS_SERVICE_OBJECT_ID,
    BACKFILL_STATUS_CAPABILITY_ID: BACKFILL_STATUS_SERVICE_OBJECT_ID,
    SYNC_RERUN_CAPABILITY_ID: SYNC_RERUN_SERVICE_OBJECT_ID,
    SYNC_BACKFILL_CAPABILITY_ID: SYNC_BACKFILL_SERVICE_OBJECT_ID,
    QUALITY_REPORT_CAPABILITY_ID: QUALITY_REPORT_SERVICE_OBJECT_ID,
}


def _unique_strings(values: Iterable[str | None]) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()
    for value in values:
        if not value:
            continue
        if value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return ordered


def _build_operator_extensions(*, surface_source: str, state_snapshot_path: str | None) -> dict[str, Any]:
    extensions: dict[str, Any] = {
        'owner_surface': 'operator_surface',
        'surface_source': surface_source,
    }
    if state_snapshot_path:
        extensions['state_snapshot'] = state_snapshot_path
    return extensions


def _build_pending_readiness_response(
    *,
    request_id: str,
    trace_ref: str,
    capability_id: str,
    target_scope_ref: str,
    target_business_date: str,
    reason_code: str,
    surface_source: str,
    state_snapshot_path: str | None = None,
) -> dict[str, Any]:
    return {
        'request_id': request_id,
        'trace_ref': trace_ref,
        'capability_id': capability_id,
        'readiness_status': 'pending',
        'evaluated_scope_ref': target_scope_ref,
        'requested_business_date': target_business_date,
        'latest_usable_business_date': target_business_date,
        'reason_codes': [reason_code],
        'blocking_dependencies': [
            {
                'dependency_kind': 'owner_surface',
                'dependency_ref': capability_id,
                'blocking_reason_code': reason_code,
                'state_trace_refs': [],
                'run_trace_refs': [],
            }
        ],
        'state_trace_refs': [],
        'run_trace_refs': [],
        'evaluated_at': utcnow_iso(),
        'extensions': _build_operator_extensions(
            surface_source=surface_source,
            state_snapshot_path=state_snapshot_path,
        ),
    }


def _build_ready_readiness_response(
    *,
    request_id: str,
    trace_ref: str,
    capability_id: str,
    target_scope_ref: str,
    target_business_date: str,
    state_trace_refs: Iterable[str],
    run_trace_refs: Iterable[str],
    surface_source: str,
    state_snapshot_path: str | None = None,
) -> dict[str, Any]:
    return {
        'request_id': request_id,
        'trace_ref': trace_ref,
        'capability_id': capability_id,
        'readiness_status': 'ready',
        'evaluated_scope_ref': target_scope_ref,
        'requested_business_date': target_business_date,
        'latest_usable_business_date': target_business_date,
        'reason_codes': [],
        'blocking_dependencies': [],
        'state_trace_refs': _unique_strings(state_trace_refs),
        'run_trace_refs': _unique_strings(run_trace_refs),
        'evaluated_at': utcnow_iso(),
        'extensions': _build_operator_extensions(
            surface_source=surface_source,
            state_snapshot_path=state_snapshot_path,
        ),
    }


def _build_scope_mismatch_service_response(
    *,
    request_id: str,
    trace_ref: str,
    capability_id: str,
    service_object_id: str,
    target_business_date: str,
    reason_codes: Iterable[str],
    surface_source: str,
    state_snapshot_path: str | None = None,
) -> dict[str, Any]:
    return {
        'request_id': request_id,
        'trace_ref': trace_ref,
        'capability_id': capability_id,
        'service_object_id': service_object_id,
        'service_status': 'scope_mismatch',
        'service_object': {},
        'data_window': {
            'from': target_business_date,
            'to': target_business_date,
        },
        'explanation_object': {
            'capability_id': capability_id,
            'explanation_scope': 'service',
            'reason_codes': list(reason_codes),
            'state_trace_refs': [],
            'run_trace_refs': [],
            'extensions': _build_operator_extensions(
                surface_source=surface_source,
                state_snapshot_path=state_snapshot_path,
            ),
        },
        'state_trace_refs': [],
        'run_trace_refs': [],
        'served_at': utcnow_iso(),
        'extensions': _build_operator_extensions(
            surface_source=surface_source,
            state_snapshot_path=state_snapshot_path,
        ),
    }


def _build_not_ready_service_response(
    *,
    request_id: str,
    trace_ref: str,
    capability_id: str,
    service_object_id: str,
    target_business_date: str,
    reason_codes: Iterable[str],
    surface_source: str,
    state_snapshot_path: str | None = None,
) -> dict[str, Any]:
    reason_codes_list = list(reason_codes)
    return {
        'request_id': request_id,
        'trace_ref': trace_ref,
        'capability_id': capability_id,
        'service_object_id': service_object_id,
        'service_status': 'not_ready',
        'service_object': {},
        'data_window': {
            'from': target_business_date,
            'to': target_business_date,
        },
        'explanation_object': {
            'capability_id': capability_id,
            'explanation_scope': 'service',
            'reason_codes': reason_codes_list,
            'summary_tokens': [capability_id, 'not_ready', target_business_date],
            'state_trace_refs': [],
            'run_trace_refs': [],
            'extensions': _build_operator_extensions(
                surface_source=surface_source,
                state_snapshot_path=state_snapshot_path,
            ),
        },
        'state_trace_refs': [],
        'run_trace_refs': [],
        'served_at': utcnow_iso(),
        'extensions': _build_operator_extensions(
            surface_source=surface_source,
            state_snapshot_path=state_snapshot_path,
        ),
    }


def _build_served_service_response(
    *,
    request_id: str,
    trace_ref: str,
    capability_id: str,
    service_object_id: str,
    service_object: dict[str, Any],
    data_window: dict[str, Any],
    state_trace_refs: Iterable[str],
    run_trace_refs: Iterable[str],
    surface_source: str,
    state_snapshot_path: str | None = None,
) -> dict[str, Any]:
    return {
        'request_id': request_id,
        'trace_ref': trace_ref,
        'capability_id': capability_id,
        'service_object_id': service_object_id,
        'service_status': 'served',
        'service_object': service_object,
        'data_window': data_window,
        'state_trace_refs': _unique_strings(state_trace_refs),
        'run_trace_refs': _unique_strings(run_trace_refs),
        'served_at': utcnow_iso(),
        'extensions': _build_operator_extensions(
            surface_source=surface_source,
            state_snapshot_path=state_snapshot_path,
        ),
    }


def _validate_supported_operator_pair(
    *,
    capability_id: str,
    service_object_id: str,
) -> bool:
    expected_service_object_id = SUPPORTED_OPERATOR_SERVICE_OBJECT_IDS.get(capability_id)
    return expected_service_object_id == service_object_id


def _build_single_report(
    *,
    truth_store: PostgresTruthSubstrate,
    capability_id: str,
    org_id: str,
) -> dict[str, Any]:
    if capability_id == SYNC_STATUS_CAPABILITY_ID:
        return truth_store.build_sync_status_report(org_id=org_id)
    if capability_id == BACKFILL_STATUS_CAPABILITY_ID:
        return truth_store.build_backfill_status_report(org_id=org_id)
    if capability_id == QUALITY_REPORT_CAPABILITY_ID:
        return truth_store.build_quality_report(org_id=org_id)
    raise KeyError(f'Unsupported operator report capability_id: {capability_id}')


def _collect_report_trace_refs(
    *,
    capability_id: str,
    report: dict[str, Any],
) -> tuple[list[str], list[str]]:
    state_trace_refs: list[str] = []
    run_trace_refs: list[str] = []

    if capability_id == SYNC_STATUS_CAPABILITY_ID:
        state_trace_refs.extend(
            item.get('state_trace_ref')
            for item in report.get('latest_sync_states', [])
        )
        for item in report.get('latest_sync_states', []):
            run_trace_refs.extend(
                [
                    item.get('latest_run_trace_ref'),
                    item.get('last_attempted_run_trace_ref'),
                ]
            )
        for scheduler_run in report.get('scheduler_runs', []):
            run_trace_refs.extend(scheduler_run.get('execution_trace_refs', []))
    elif capability_id == BACKFILL_STATUS_CAPABILITY_ID:
        state_trace_refs.extend(
            item.get('state_trace_ref')
            for item in report.get('backfill_progress_states', [])
        )
    elif capability_id == QUALITY_REPORT_CAPABILITY_ID:
        state_trace_refs.extend(
            item.get('snapshot_trace_ref')
            for item in report.get('field_coverage_snapshots', [])
        )
        state_trace_refs.extend(
            item.get('snapshot_trace_ref')
            for item in report.get('schema_alignment_snapshots', [])
        )
        state_trace_refs.extend(
            item.get('state_trace_ref')
            for item in report.get('quality_issues', [])
        )
        run_trace_refs.extend(
            item.get('run_trace_ref')
            for item in report.get('field_coverage_snapshots', [])
        )
        run_trace_refs.extend(
            item.get('run_trace_ref')
            for item in report.get('schema_alignment_snapshots', [])
        )
        run_trace_refs.extend(
            item.get('run_trace_ref')
            for item in report.get('quality_issues', [])
        )
    else:
        raise KeyError(f'Unsupported operator report capability_id: {capability_id}')

    return _unique_strings(state_trace_refs), _unique_strings(run_trace_refs)


def _normalize_backfill_window(
    *,
    requested_business_date: str,
    backfill_from: str | None,
    backfill_to: str | None,
) -> tuple[str | None, str | None]:
    if backfill_from and not backfill_to:
        return backfill_from, backfill_from
    if backfill_to and not backfill_from:
        return backfill_to, backfill_to
    if backfill_from or backfill_to:
        return backfill_from, backfill_to
    return None, requested_business_date


def build_operator_status_bundle(
    *,
    truth_store: PostgresTruthSubstrate,
    org_ids: Iterable[str],
) -> dict[str, Any]:
    ordered_org_ids = list(org_ids)
    return {
        'sync_status': [
            truth_store.build_sync_status_report(org_id=org_id)
            for org_id in ordered_org_ids
        ],
        'backfill_status': [
            truth_store.build_backfill_status_report(org_id=org_id)
            for org_id in ordered_org_ids
        ],
        'quality_report': [
            truth_store.build_quality_report(org_id=org_id)
            for org_id in ordered_org_ids
        ],
    }


def query_operator_status_from_snapshot(
    *,
    request_id: str,
    trace_ref: str,
    state_snapshot_path: str | Path,
    org_ids: Iterable[str],
) -> dict[str, Any]:
    truth_store = PostgresTruthSubstrate.from_snapshot_file(state_snapshot_path)
    payload = build_operator_status_bundle(
        truth_store=truth_store,
        org_ids=org_ids,
    )
    payload['request_id'] = request_id
    payload['trace_ref'] = trace_ref
    payload['state_snapshot'] = str(Path(state_snapshot_path))
    return payload


def _build_operator_status_service(
    *,
    request_id: str,
    trace_ref: str,
    target_scope_ref: str,
    target_business_date: str,
    capability_id: str,
    service_object_id: str,
    org_id: str,
    state_snapshot_path: str,
    freshness_mode: str | None,
    backfill_from: str | None,
    backfill_to: str | None,
) -> dict[str, Any]:
    truth_store = PostgresTruthSubstrate.from_snapshot_file(state_snapshot_path)
    report = _build_single_report(
        truth_store=truth_store,
        capability_id=capability_id,
        org_id=org_id,
    )
    state_trace_refs, run_trace_refs = _collect_report_trace_refs(
        capability_id=capability_id,
        report=report,
    )
    backfill_window_from, backfill_window_to = _normalize_backfill_window(
        requested_business_date=target_business_date,
        backfill_from=backfill_from,
        backfill_to=backfill_to,
    )
    readiness_response = _build_ready_readiness_response(
        request_id=request_id,
        trace_ref=trace_ref,
        capability_id=capability_id,
        target_scope_ref=target_scope_ref,
        target_business_date=target_business_date,
        state_trace_refs=state_trace_refs,
        run_trace_refs=run_trace_refs,
        surface_source='persisted_snapshot',
        state_snapshot_path=state_snapshot_path,
    )
    service_object = {
        'capability_id': capability_id,
        'service_object_id': service_object_id,
        'org_id': org_id,
        'requested_business_date': target_business_date,
        'freshness_mode': freshness_mode,
        'requested_backfill_window': {
            'from': backfill_window_from,
            'to': backfill_window_to,
        },
        'state_snapshot': state_snapshot_path,
        'report': report,
    }
    service_response = _build_served_service_response(
        request_id=request_id,
        trace_ref=trace_ref,
        capability_id=capability_id,
        service_object_id=service_object_id,
        service_object=service_object,
        data_window={
            'from': backfill_window_from or target_business_date,
            'to': backfill_window_to or target_business_date,
        },
        state_trace_refs=state_trace_refs,
        run_trace_refs=run_trace_refs,
        surface_source='persisted_snapshot',
        state_snapshot_path=state_snapshot_path,
    )
    return {
        'readiness_response': readiness_response,
        'theme_service_response': service_response,
    }


def _build_temporal_plane(
    *,
    truth_store: PostgresTruthSubstrate,
    app_secret: str,
    backfill_start_business_date: str,
) -> TemporalNightlySyncPlane:
    policy = NightlyPlannerPolicy.from_registry(
        backfill_start_business_date=backfill_start_business_date,
    )
    planner = NightlySyncPlanner(
        truth_store=truth_store,
        policy=policy,
    )
    runtime = NightlySyncRuntime(
        truth_store=truth_store,
        planner_policy=policy,
        app_secret=app_secret,
    )
    return TemporalNightlySyncPlane(
        truth_store=truth_store,
        planner=planner,
        runtime=runtime,
        worker_bootstrap=TemporalWorkerBootstrap.from_registry(),
    )


def _execute_operator_action(
    *,
    request_id: str,
    trace_ref: str,
    target_scope_ref: str,
    target_business_date: str,
    capability_id: str,
    service_object_id: str,
    org_id: str,
    state_snapshot_path: str,
    app_secret: str,
    transport: Any,
    backfill_from: str | None,
    backfill_to: str | None,
    rerun_mode: str | None,
) -> dict[str, Any]:
    truth_store = PostgresTruthSubstrate.from_snapshot_file(state_snapshot_path)
    if capability_id == SYNC_RERUN_CAPABILITY_ID:
        temporal_plane = _build_temporal_plane(
            truth_store=truth_store,
            app_secret=app_secret,
            backfill_start_business_date=target_business_date,
        )
        action_result = temporal_plane.run_rerun_workflow(
            org_id=org_id,
            business_date=target_business_date,
            transport=transport,
        )
        requested_window = {
            'from': target_business_date,
            'to': target_business_date,
        }
        action_parameters = {
            'rerun_mode': rerun_mode,
        }
    elif capability_id == SYNC_BACKFILL_CAPABILITY_ID:
        requested_from, requested_to = _normalize_backfill_window(
            requested_business_date=target_business_date,
            backfill_from=backfill_from,
            backfill_to=backfill_to,
        )
        if (
            (requested_from is None or requested_to is None)
            and should_default_operator_backfill_to_full_history(SOURCE_SYSTEM_ID)
        ):
            resolved_history_start = resolve_nightly_sync_history_start_business_date(SOURCE_SYSTEM_ID)
            if resolved_history_start:
                requested_from = resolved_history_start
                requested_to = target_business_date
        if requested_from is None or requested_to is None:
            raise ValueError('backfill action requires backfill_from or backfill_to')
        temporal_plane = _build_temporal_plane(
            truth_store=truth_store,
            app_secret=app_secret,
            backfill_start_business_date=requested_from,
        )
        action_result = temporal_plane.run_backfill_workflow(
            org_id=org_id,
            backfill_from_business_date=requested_from,
            backfill_to_business_date=requested_to,
            transport=transport,
        )
        requested_window = {
            'from': requested_from,
            'to': requested_to,
        }
        action_parameters = {
            'backfill_from': requested_from,
            'backfill_to': requested_to,
        }
    else:
        raise KeyError(f'Unsupported operator action capability_id: {capability_id}')

    Path(state_snapshot_path).parent.mkdir(parents=True, exist_ok=True)
    truth_store.write_snapshot_file(state_snapshot_path)
    post_action_bundle = build_operator_status_bundle(
        truth_store=truth_store,
        org_ids=[org_id],
    )
    status_report = post_action_bundle['sync_status'][0]
    backfill_report = post_action_bundle['backfill_status'][0]
    quality_report = post_action_bundle['quality_report'][0]
    status_state_trace_refs, status_run_trace_refs = _collect_report_trace_refs(
        capability_id=SYNC_STATUS_CAPABILITY_ID,
        report=status_report,
    )
    backfill_state_trace_refs, backfill_run_trace_refs = _collect_report_trace_refs(
        capability_id=BACKFILL_STATUS_CAPABILITY_ID,
        report=backfill_report,
    )
    quality_state_trace_refs, quality_run_trace_refs = _collect_report_trace_refs(
        capability_id=QUALITY_REPORT_CAPABILITY_ID,
        report=quality_report,
    )
    outcome_run_trace_refs = [
        outcome.get('run_trace_ref')
        for outcome in action_result.get('outcomes', [action_result.get('outcome', {})])
    ]
    service_state_trace_refs = _unique_strings(
        [
            *status_state_trace_refs,
            *backfill_state_trace_refs,
            *quality_state_trace_refs,
        ]
    )
    service_run_trace_refs = _unique_strings(
        [
            *status_run_trace_refs,
            *backfill_run_trace_refs,
            *quality_run_trace_refs,
            *outcome_run_trace_refs,
        ]
    )
    readiness_response = _build_ready_readiness_response(
        request_id=request_id,
        trace_ref=trace_ref,
        capability_id=capability_id,
        target_scope_ref=target_scope_ref,
        target_business_date=target_business_date,
        state_trace_refs=service_state_trace_refs,
        run_trace_refs=service_run_trace_refs,
        surface_source='temporal_action',
        state_snapshot_path=state_snapshot_path,
    )
    service_object = {
        'capability_id': capability_id,
        'service_object_id': service_object_id,
        'org_id': org_id,
        'action_kind': 'rerun_sync' if capability_id == SYNC_RERUN_CAPABILITY_ID else 'trigger_backfill',
        'requested_business_date': target_business_date,
        'requested_window': requested_window,
        'action_parameters': action_parameters,
        'state_snapshot': state_snapshot_path,
        'action_result': action_result,
        'post_action_reports': {
            'sync_status': status_report,
            'backfill_status': backfill_report,
            'quality_report': quality_report,
        },
    }
    service_response = _build_served_service_response(
        request_id=request_id,
        trace_ref=trace_ref,
        capability_id=capability_id,
        service_object_id=service_object_id,
        service_object=service_object,
        data_window=requested_window,
        state_trace_refs=service_state_trace_refs,
        run_trace_refs=service_run_trace_refs,
        surface_source='temporal_action',
        state_snapshot_path=state_snapshot_path,
    )
    return {
        'readiness_response': readiness_response,
        'theme_service_response': service_response,
        'state_snapshot': state_snapshot_path,
    }


def run_operator_surface(
    *,
    request_id: str,
    trace_ref: str,
    target_scope_ref: str,
    target_business_date: str,
    capability_id: str,
    service_object_id: str,
    org_id: str | None,
    state_snapshot_path: str | None,
    freshness_mode: str | None = None,
    backfill_from: str | None = None,
    backfill_to: str | None = None,
    rerun_mode: str | None = None,
    transport: Any | None = None,
    app_secret: str | None = None,
) -> dict[str, Any]:
    if capability_id not in READ_ONLY_OPERATOR_CAPABILITIES.union(ACTION_OPERATOR_CAPABILITIES):
        return {
            'readiness_response': _build_pending_readiness_response(
                request_id=request_id,
                trace_ref=trace_ref,
                capability_id=capability_id,
                target_scope_ref=target_scope_ref,
                target_business_date=target_business_date,
                reason_code='capability_not_registered',
                surface_source='operator_surface',
                state_snapshot_path=state_snapshot_path,
            ),
            'theme_service_response': _build_scope_mismatch_service_response(
                request_id=request_id,
                trace_ref=trace_ref,
                capability_id=capability_id,
                service_object_id=service_object_id,
                target_business_date=target_business_date,
                reason_codes=['capability_not_registered'],
                surface_source='operator_surface',
                state_snapshot_path=state_snapshot_path,
            ),
        }

    if org_id is None:
        return {
            'readiness_response': _build_pending_readiness_response(
                request_id=request_id,
                trace_ref=trace_ref,
                capability_id=capability_id,
                target_scope_ref=target_scope_ref,
                target_business_date=target_business_date,
                reason_code='missing_org_context',
                surface_source='operator_surface',
                state_snapshot_path=state_snapshot_path,
            ),
            'theme_service_response': _build_not_ready_service_response(
                request_id=request_id,
                trace_ref=trace_ref,
                capability_id=capability_id,
                service_object_id=service_object_id,
                target_business_date=target_business_date,
                reason_codes=['missing_org_context'],
                surface_source='operator_surface',
                state_snapshot_path=state_snapshot_path,
            ),
        }

    resolved_service_object_id = service_object_id or SUPPORTED_OPERATOR_SERVICE_OBJECT_IDS.get(capability_id)

    if resolved_service_object_id is None:
        return {
            'readiness_response': _build_pending_readiness_response(
                request_id=request_id,
                trace_ref=trace_ref,
                capability_id=capability_id,
                target_scope_ref=target_scope_ref,
                target_business_date=target_business_date,
                reason_code='capability_not_registered',
                surface_source='operator_surface',
                state_snapshot_path=state_snapshot_path,
            ),
            'theme_service_response': _build_scope_mismatch_service_response(
                request_id=request_id,
                trace_ref=trace_ref,
                capability_id=capability_id,
                service_object_id=service_object_id or '',
                target_business_date=target_business_date,
                reason_codes=['capability_not_registered'],
                surface_source='operator_surface',
                state_snapshot_path=state_snapshot_path,
            ),
        }

    if service_object_id is not None and not _validate_supported_operator_pair(
        capability_id=capability_id,
        service_object_id=service_object_id,
    ):
        return {
            'readiness_response': _build_ready_readiness_response(
                request_id=request_id,
                trace_ref=trace_ref,
                capability_id=capability_id,
                target_scope_ref=target_scope_ref,
                target_business_date=target_business_date,
                state_trace_refs=[],
                run_trace_refs=[],
                surface_source='operator_surface',
                state_snapshot_path=state_snapshot_path,
            ),
            'theme_service_response': _build_scope_mismatch_service_response(
                request_id=request_id,
                trace_ref=trace_ref,
                capability_id=capability_id,
                service_object_id=service_object_id,
                target_business_date=target_business_date,
                reason_codes=['scope_out_of_contract'],
                surface_source='operator_surface',
                state_snapshot_path=state_snapshot_path,
            ),
        }

    if not state_snapshot_path:
        return {
            'readiness_response': _build_pending_readiness_response(
                request_id=request_id,
                trace_ref=trace_ref,
                capability_id=capability_id,
                target_scope_ref=target_scope_ref,
                target_business_date=target_business_date,
                reason_code='missing_persisted_state_path',
                surface_source='operator_surface',
            ),
            'theme_service_response': _build_not_ready_service_response(
                request_id=request_id,
                trace_ref=trace_ref,
                capability_id=capability_id,
                service_object_id=service_object_id,
                target_business_date=target_business_date,
                reason_codes=['missing_persisted_state_path'],
                surface_source='operator_surface',
            ),
        }

    normalized_state_snapshot_path = str(Path(state_snapshot_path))
    if capability_id in READ_ONLY_OPERATOR_CAPABILITIES:
        return _build_operator_status_service(
            request_id=request_id,
            trace_ref=trace_ref,
            target_scope_ref=target_scope_ref,
            target_business_date=target_business_date,
            capability_id=capability_id,
            service_object_id=resolved_service_object_id,
            org_id=org_id,
            state_snapshot_path=normalized_state_snapshot_path,
            freshness_mode=freshness_mode,
            backfill_from=backfill_from,
            backfill_to=backfill_to,
        )

    if app_secret is None:
        return {
            'readiness_response': _build_pending_readiness_response(
                request_id=request_id,
                trace_ref=trace_ref,
                capability_id=capability_id,
                target_scope_ref=target_scope_ref,
                target_business_date=target_business_date,
                reason_code='missing_app_secret',
                surface_source='operator_surface',
                state_snapshot_path=normalized_state_snapshot_path,
            ),
            'theme_service_response': _build_not_ready_service_response(
                request_id=request_id,
                trace_ref=trace_ref,
                capability_id=capability_id,
                service_object_id=service_object_id,
                target_business_date=target_business_date,
                reason_codes=['missing_app_secret'],
                surface_source='operator_surface',
                state_snapshot_path=normalized_state_snapshot_path,
            ),
        }

    if transport is None:
        return {
            'readiness_response': _build_pending_readiness_response(
                request_id=request_id,
                trace_ref=trace_ref,
                capability_id=capability_id,
                target_scope_ref=target_scope_ref,
                target_business_date=target_business_date,
                reason_code='missing_operator_transport',
                surface_source='operator_surface',
                state_snapshot_path=normalized_state_snapshot_path,
            ),
            'theme_service_response': _build_not_ready_service_response(
                request_id=request_id,
                trace_ref=trace_ref,
                capability_id=capability_id,
                service_object_id=service_object_id,
                target_business_date=target_business_date,
                reason_codes=['missing_operator_transport'],
                surface_source='operator_surface',
                state_snapshot_path=normalized_state_snapshot_path,
            ),
        }

    return _execute_operator_action(
        request_id=request_id,
            trace_ref=trace_ref,
            target_scope_ref=target_scope_ref,
            target_business_date=target_business_date,
            capability_id=capability_id,
            service_object_id=resolved_service_object_id,
            org_id=org_id,
            state_snapshot_path=normalized_state_snapshot_path,
            app_secret=app_secret,
            transport=transport,
        backfill_from=backfill_from,
        backfill_to=backfill_to,
        rerun_mode=rerun_mode,
    )
