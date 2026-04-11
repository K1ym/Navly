#!/usr/bin/env bash
set -euo pipefail

python3 platforms/data-platform/scripts/phase1_remaining_live_transport_validation_matrix.py > /dev/null
python3 -m unittest platforms/data-platform/tests/test_finance_summary_vertical_slice.py
python3 -m unittest platforms/data-platform/tests/test_staff_board_vertical_slice.py
python3 -m unittest platforms/data-platform/tests/test_commission_setting_governance_surface.py
python3 -m unittest platforms/data-platform/tests/test_phase1_live_transport_validation_matrix.py
