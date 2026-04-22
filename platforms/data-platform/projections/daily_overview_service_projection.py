from __future__ import annotations

from typing import Any


DAILY_OVERVIEW_CAPABILITY_ID = 'navly.store.daily_overview'
DAILY_OVERVIEW_SERVICE_OBJECT_ID = 'navly.service.store.daily_overview'


def build_daily_overview_service_object(
    *,
    target_scope_ref: str,
    target_business_date: str,
    latest_usable_business_date: str,
    business_day_policy: dict[str, Any],
    member_insight_service_response: dict[str, Any],
    staff_board_service_response: dict[str, Any],
    finance_summary_service_response: dict[str, Any],
) -> dict[str, Any]:
    published_service_object_ids = [
        member_insight_service_response['service_object_id'],
        staff_board_service_response['service_object_id'],
        finance_summary_service_response['service_object_id'],
    ]
    return {
        'capability_id': DAILY_OVERVIEW_CAPABILITY_ID,
        'service_object_id': DAILY_OVERVIEW_SERVICE_OBJECT_ID,
        'target_scope_ref': target_scope_ref,
        'target_business_date': target_business_date,
        'latest_usable_business_date': latest_usable_business_date,
        'business_day_boundary_policy': {
            'policy_id': business_day_policy['policy_id'],
            'metric_domain': business_day_policy.get('metric_domain'),
            'scope_kind': business_day_policy.get('scope_kind'),
            'scope_ref': business_day_policy.get('scope_ref'),
            'selector_kind': business_day_policy['selector_kind'],
            'timezone': business_day_policy['timezone'],
            'business_day_start_local_time': business_day_policy.get('business_day_start_local_time'),
            'business_day_end_exclusive_local_time': business_day_policy.get('business_day_end_exclusive_local_time'),
            'business_day_boundary_local_time': business_day_policy['business_day_boundary_local_time'],
        },
        'published_service_object_ids': published_service_object_ids,
        'member_insight': member_insight_service_response['service_object'],
        'staff_board': staff_board_service_response['service_object'],
        'finance_summary': finance_summary_service_response['service_object'],
    }
