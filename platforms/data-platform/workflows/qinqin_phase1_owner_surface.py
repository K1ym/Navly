from __future__ import annotations

from typing import Any

from backbone_support.latest_usable_state_backbone import utcnow_iso
from backbone_support.qinqin_phase1_owner_surface_registry import (
    CAPABILITY_EXPLANATION_CAPABILITY_ID,
    CAPABILITY_EXPLANATION_SERVICE_OBJECT_ID,
    DAILY_OVERVIEW_CAPABILITY_ID,
    DAILY_OVERVIEW_SERVICE_OBJECT_ID,
    FINANCE_SUMMARY_CAPABILITY_ID,
    FINANCE_SUMMARY_SERVICE_OBJECT_ID,
    MEMBER_INSIGHT_CAPABILITY_ID,
    MEMBER_INSIGHT_SERVICE_OBJECT_ID,
    STAFF_BOARD_CAPABILITY_ID,
    STAFF_BOARD_SERVICE_OBJECT_ID,
)
from completeness.qinqin_phase1_readiness_surface import build_qinqin_phase1_readiness_response
from ingestion.qinqin_capability_slice import run_qinqin_capability_slice
from serving.qinqin_phase1_theme_service_surface import (
    build_capability_explanation_theme_service_response,
    build_capability_explanation_object,
    build_daily_overview_theme_service_response,
    build_qinqin_phase1_theme_service_response,
)
from workflows.member_insight_owner_surface import (
    build_member_insight_owner_surface,
    query_member_insight_capability_readiness,
    query_member_insight_theme_service,
)


PHASE1_SERVICE_SET = {
    MEMBER_INSIGHT_CAPABILITY_ID: MEMBER_INSIGHT_SERVICE_OBJECT_ID,
    FINANCE_SUMMARY_CAPABILITY_ID: FINANCE_SUMMARY_SERVICE_OBJECT_ID,
    STAFF_BOARD_CAPABILITY_ID: STAFF_BOARD_SERVICE_OBJECT_ID,
    DAILY_OVERVIEW_CAPABILITY_ID: DAILY_OVERVIEW_SERVICE_OBJECT_ID,
    CAPABILITY_EXPLANATION_CAPABILITY_ID: CAPABILITY_EXPLANATION_SERVICE_OBJECT_ID,
}


def _aggregate_daily_overview_readiness(
    *,
    request_id: str,
    trace_ref: str,
    target_scope_ref: str,
    target_business_date: str,
    component_surfaces: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    component_readiness = [
        component_surfaces['member_insight']['readiness_response'],
        component_surfaces['finance_summary']['readiness_response'],
        component_surfaces['staff_board']['readiness_response'],
    ]
    readiness_statuses = {entry['readiness_status'] for entry in component_readiness}
    latest_dates = [
        entry.get('latest_usable_business_date')
        for entry in component_readiness
        if entry.get('latest_usable_business_date')
    ]
    if readiness_statuses == {'ready'}:
        readiness_status = 'ready'
        reason_codes: list[str] = []
    elif 'failed' in readiness_statuses:
        readiness_status = 'failed'
        reason_codes = ['dependency_failed']
    else:
        readiness_status = 'pending'
        reason_codes = ['missing_dependency']
    state_trace_refs = []
    run_trace_refs = []
    blocking_dependencies = []
    for component in component_readiness:
        state_trace_refs.extend(component.get('state_trace_refs', []))
        run_trace_refs.extend(component.get('run_trace_refs', []))
        blocking_dependencies.extend(component.get('blocking_dependencies', []))
    latest_usable_business_date = min(latest_dates) if latest_dates else target_business_date
    return {
        'request_id': request_id,
        'trace_ref': trace_ref,
        'capability_id': DAILY_OVERVIEW_CAPABILITY_ID,
        'readiness_status': readiness_status,
        'evaluated_scope_ref': target_scope_ref,
        'requested_business_date': target_business_date,
        'latest_usable_business_date': latest_usable_business_date,
        'reason_codes': reason_codes,
        'blocking_dependencies': blocking_dependencies,
        'state_trace_refs': state_trace_refs,
        'run_trace_refs': run_trace_refs,
        'evaluated_at': utcnow_iso(),
        'extensions': {
            'owner_surface': 'daily_overview',
            'component_readiness_statuses': {
                'member_insight': component_surfaces['member_insight']['readiness_response']['readiness_status'],
                'finance_summary': component_surfaces['finance_summary']['readiness_response']['readiness_status'],
                'staff_board': component_surfaces['staff_board']['readiness_response']['readiness_status'],
            },
        },
    }


def _capability_explanation_owner_surface(
    *,
    request_id: str,
    trace_ref: str,
    target_scope_ref: str,
    target_business_date: str,
    requested_capability_id: str,
    requested_service_object_id: str,
    explanation_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    context = dict(explanation_context or {})
    state_trace_refs = list(context.get('state_trace_refs', []))
    run_trace_refs = list(context.get('run_trace_refs', []))
    readiness_response = {
        'request_id': request_id,
        'trace_ref': trace_ref,
        'capability_id': CAPABILITY_EXPLANATION_CAPABILITY_ID,
        'readiness_status': 'ready',
        'evaluated_scope_ref': target_scope_ref,
        'requested_business_date': target_business_date,
        'latest_usable_business_date': target_business_date,
        'reason_codes': [],
        'blocking_dependencies': [],
        'state_trace_refs': state_trace_refs,
        'run_trace_refs': run_trace_refs,
        'evaluated_at': utcnow_iso(),
        'extensions': {
            'owner_surface': 'capability_explanation',
            'companion_explanation_object': build_capability_explanation_object(
                capability_id=context.get('explained_capability_id') or CAPABILITY_EXPLANATION_CAPABILITY_ID,
                explanation_scope=str(context.get('explanation_scope') or 'service'),
                reason_codes=list(context.get('reason_codes', [])),
                state_trace_refs=state_trace_refs,
                run_trace_refs=run_trace_refs,
                owner_surface='capability_explanation',
                latest_usable_business_date=target_business_date,
                summary_tokens=list(context.get('summary_tokens', [])),
                extensions={
                    'explained_service_object_id': context.get('explained_service_object_id'),
                    'suggested_next_action': context.get('suggested_next_action'),
                },
            ),
        },
    }
    theme_service_response = build_capability_explanation_theme_service_response(
        request_id=request_id,
        trace_ref=trace_ref,
        target_scope_ref=target_scope_ref,
        target_business_date=target_business_date,
        readiness_response=readiness_response,
        requested_capability_id=requested_capability_id,
        requested_service_object_id=requested_service_object_id,
        explanation_context=context,
    )
    return {
        'readiness_response': readiness_response,
        'theme_service_response': theme_service_response,
        'vertical_slice_result': None,
    }


def _data_backed_phase1_owner_surface(
    *,
    request_id: str,
    trace_ref: str,
    target_scope_ref: str,
    target_business_date: str,
    requested_capability_id: str,
    requested_service_object_id: str,
    org_id: str,
    start_time: str,
    end_time: str,
    app_secret: str,
    transport: Any,
) -> dict[str, Any]:
    vertical_slice_result = run_qinqin_capability_slice(
        capability_id=requested_capability_id,
        org_id=org_id,
        start_time=start_time,
        end_time=end_time,
        requested_business_date=target_business_date,
        app_secret=app_secret,
        transport=transport,
    )
    readiness_response = build_qinqin_phase1_readiness_response(
        request_id=request_id,
        trace_ref=trace_ref,
        target_scope_ref=target_scope_ref,
        target_business_date=target_business_date,
        vertical_slice_result=vertical_slice_result,
        requested_capability_id=requested_capability_id,
    )
    theme_service_response = build_qinqin_phase1_theme_service_response(
        request_id=request_id,
        trace_ref=trace_ref,
        target_scope_ref=target_scope_ref,
        target_business_date=target_business_date,
        readiness_response=readiness_response,
        vertical_slice_result=vertical_slice_result,
        requested_capability_id=requested_capability_id,
        requested_service_object_id=requested_service_object_id,
    )
    return {
        'vertical_slice_result': vertical_slice_result,
        'readiness_response': readiness_response,
        'theme_service_response': theme_service_response,
    }


def build_qinqin_phase1_owner_surface(
    *,
    request_id: str,
    trace_ref: str,
    target_scope_ref: str,
    target_business_date: str,
    requested_capability_id: str,
    requested_service_object_id: str,
    org_id: str | None = None,
    start_time: str | None = None,
    end_time: str | None = None,
    app_secret: str | None = None,
    transport: Any | None = None,
    explanation_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if requested_capability_id == MEMBER_INSIGHT_CAPABILITY_ID:
        result = build_member_insight_owner_surface(
            request_id=request_id,
            trace_ref=trace_ref,
            target_scope_ref=target_scope_ref,
            target_business_date=target_business_date,
            org_id=str(org_id),
            start_time=str(start_time),
            end_time=str(end_time),
            app_secret=str(app_secret),
            transport=transport,
        )
        return {
            **result,
            'vertical_slice_result': result['vertical_slice_result'],
        }

    if requested_capability_id in {FINANCE_SUMMARY_CAPABILITY_ID, STAFF_BOARD_CAPABILITY_ID}:
        return _data_backed_phase1_owner_surface(
            request_id=request_id,
            trace_ref=trace_ref,
            target_scope_ref=target_scope_ref,
            target_business_date=target_business_date,
            requested_capability_id=requested_capability_id,
            requested_service_object_id=requested_service_object_id,
            org_id=str(org_id),
            start_time=str(start_time),
            end_time=str(end_time),
            app_secret=str(app_secret),
            transport=transport,
        )

    if requested_capability_id == DAILY_OVERVIEW_CAPABILITY_ID:
        component_surfaces = {
            'member_insight': build_qinqin_phase1_owner_surface(
                request_id=request_id,
                trace_ref=trace_ref,
                target_scope_ref=target_scope_ref,
                target_business_date=target_business_date,
                requested_capability_id=MEMBER_INSIGHT_CAPABILITY_ID,
                requested_service_object_id=MEMBER_INSIGHT_SERVICE_OBJECT_ID,
                org_id=org_id,
                start_time=start_time,
                end_time=end_time,
                app_secret=app_secret,
                transport=transport,
            ),
            'finance_summary': build_qinqin_phase1_owner_surface(
                request_id=request_id,
                trace_ref=trace_ref,
                target_scope_ref=target_scope_ref,
                target_business_date=target_business_date,
                requested_capability_id=FINANCE_SUMMARY_CAPABILITY_ID,
                requested_service_object_id=FINANCE_SUMMARY_SERVICE_OBJECT_ID,
                org_id=org_id,
                start_time=start_time,
                end_time=end_time,
                app_secret=app_secret,
                transport=transport,
            ),
            'staff_board': build_qinqin_phase1_owner_surface(
                request_id=request_id,
                trace_ref=trace_ref,
                target_scope_ref=target_scope_ref,
                target_business_date=target_business_date,
                requested_capability_id=STAFF_BOARD_CAPABILITY_ID,
                requested_service_object_id=STAFF_BOARD_SERVICE_OBJECT_ID,
                org_id=org_id,
                start_time=start_time,
                end_time=end_time,
                app_secret=app_secret,
                transport=transport,
            ),
        }
        readiness_response = _aggregate_daily_overview_readiness(
            request_id=request_id,
            trace_ref=trace_ref,
            target_scope_ref=target_scope_ref,
            target_business_date=target_business_date,
            component_surfaces=component_surfaces,
        )
        theme_service_response = build_daily_overview_theme_service_response(
            request_id=request_id,
            trace_ref=trace_ref,
            target_scope_ref=target_scope_ref,
            target_business_date=target_business_date,
            readiness_response=readiness_response,
            requested_capability_id=requested_capability_id,
            requested_service_object_id=requested_service_object_id,
            component_surfaces=component_surfaces,
        )
        return {
            'vertical_slice_result': None,
            'readiness_response': readiness_response,
            'theme_service_response': theme_service_response,
            'component_surfaces': component_surfaces,
        }

    if requested_capability_id == CAPABILITY_EXPLANATION_CAPABILITY_ID:
        return _capability_explanation_owner_surface(
            request_id=request_id,
            trace_ref=trace_ref,
            target_scope_ref=target_scope_ref,
            target_business_date=target_business_date,
            requested_capability_id=requested_capability_id,
            requested_service_object_id=requested_service_object_id,
            explanation_context=explanation_context,
        )

    raise KeyError(f'Unsupported phase-1 owner surface capability_id: {requested_capability_id}')


def query_qinqin_phase1_capability_readiness(
    *,
    request_id: str,
    trace_ref: str,
    target_scope_ref: str,
    target_business_date: str,
    requested_capability_id: str,
    org_id: str | None = None,
    start_time: str | None = None,
    end_time: str | None = None,
    app_secret: str | None = None,
    transport: Any | None = None,
    explanation_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if requested_capability_id == MEMBER_INSIGHT_CAPABILITY_ID:
        return query_member_insight_capability_readiness(
            request_id=request_id,
            trace_ref=trace_ref,
            target_scope_ref=target_scope_ref,
            target_business_date=target_business_date,
            org_id=str(org_id),
            start_time=str(start_time),
            end_time=str(end_time),
            app_secret=str(app_secret),
            transport=transport,
        )
    return build_qinqin_phase1_owner_surface(
        request_id=request_id,
        trace_ref=trace_ref,
        target_scope_ref=target_scope_ref,
        target_business_date=target_business_date,
        requested_capability_id=requested_capability_id,
        requested_service_object_id=PHASE1_SERVICE_SET[requested_capability_id],
        org_id=org_id,
        start_time=start_time,
        end_time=end_time,
        app_secret=app_secret,
        transport=transport,
        explanation_context=explanation_context,
    )['readiness_response']


def query_qinqin_phase1_theme_service(
    *,
    request_id: str,
    trace_ref: str,
    target_scope_ref: str,
    target_business_date: str,
    requested_capability_id: str,
    requested_service_object_id: str,
    org_id: str | None = None,
    start_time: str | None = None,
    end_time: str | None = None,
    app_secret: str | None = None,
    transport: Any | None = None,
    explanation_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if requested_capability_id == MEMBER_INSIGHT_CAPABILITY_ID:
        return query_member_insight_theme_service(
            request_id=request_id,
            trace_ref=trace_ref,
            target_scope_ref=target_scope_ref,
            target_business_date=target_business_date,
            org_id=str(org_id),
            start_time=str(start_time),
            end_time=str(end_time),
            app_secret=str(app_secret),
            transport=transport,
            requested_capability_id=requested_capability_id,
            requested_service_object_id=requested_service_object_id,
        )
    return build_qinqin_phase1_owner_surface(
        request_id=request_id,
        trace_ref=trace_ref,
        target_scope_ref=target_scope_ref,
        target_business_date=target_business_date,
        requested_capability_id=requested_capability_id,
        requested_service_object_id=requested_service_object_id,
        org_id=org_id,
        start_time=start_time,
        end_time=end_time,
        app_secret=app_secret,
        transport=transport,
        explanation_context=explanation_context,
    )['theme_service_response']

