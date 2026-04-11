from __future__ import annotations

from typing import Any


COMMISSION_SETTING_ENDPOINT_ID = 'qinqin.staff.get_tech_commission_set_list.v1_8'


def build_commission_setting_canonical_artifacts(
    response_envelopes: list[dict[str, Any]],
    *,
    org_id: str,
    requested_business_date: str,
) -> dict[str, list[dict[str, Any]]]:
    commission_settings: dict[str, dict[str, Any]] = {}
    commission_setting_details: list[dict[str, Any]] = []

    for row_index, envelope in enumerate(response_envelopes, start=1):
        ret_data = envelope.get('RetData')
        if not isinstance(ret_data, list):
            continue
        for item_index, item in enumerate(ret_data, start=1):
            if not isinstance(item, dict):
                continue
            commission_setting_id = str(
                item.get('ItemId')
                or f'{org_id}:{requested_business_date}:commission-setting:{row_index}:{item_index}'
            )
            commission_settings[commission_setting_id] = {
                'commission_setting_id': commission_setting_id,
                'org_id': org_id,
                'item_id': item.get('ItemId'),
                'item_name': item.get('ItemName'),
                'source_endpoint_contract_id': COMMISSION_SETTING_ENDPOINT_ID,
                'requested_business_date': requested_business_date,
            }
            for detail_index, detail in enumerate(item.get('PCBaseList') or [], start=1):
                if not isinstance(detail, dict):
                    continue
                commission_setting_details.append({
                    'commission_setting_detail_id': str(
                        detail.get('Id')
                        or f'{commission_setting_id}:detail:{detail_index}'
                    ),
                    'commission_setting_id': commission_setting_id,
                    'detail_sequence': detail_index,
                    'item_id': detail.get('ItemId') or item.get('ItemId'),
                    'item_name': detail.get('ItemName') or item.get('ItemName'),
                    'org_id': detail.get('OrgId') or org_id,
                    'state': detail.get('State'),
                    'sex': detail.get('Sex'),
                    'buy_amount': detail.get('Buy'),
                    'appoint_amount': detail.get('Appoint'),
                    'call_amount': detail.get('Call'),
                    'wheel_amount': detail.get('Wheel'),
                    'add_amount': detail.get('Add'),
                    'amount': detail.get('Amount'),
                    'multiple': detail.get('Multiple'),
                    'base_commission_channel': detail.get('BaseCommissionChannel'),
                    'over_commission_channel': detail.get('OverCommissionChannel'),
                    'add_commission_channel': detail.get('AddCommissionChannel'),
                    'operated_at': detail.get('OptTime'),
                    'payload': detail,
                    'source_endpoint_contract_id': COMMISSION_SETTING_ENDPOINT_ID,
                    'requested_business_date': requested_business_date,
                })

    return {
        'commission_setting': list(commission_settings.values()),
        'commission_setting_detail': commission_setting_details,
    }


__all__ = ['build_commission_setting_canonical_artifacts']
