#!/usr/bin/env bash
set -euo pipefail

python3 -m unittest platforms/data-platform/tests/test_qinqin_contract_governance.py
python3 -m unittest platforms/data-platform/tests/test_member_insight_vertical_slice.py
python3 -m unittest platforms/data-platform/tests/test_member_insight_owner_surface.py
bash platforms/auth-kernel/scripts/validate-milestone-b.sh
bash runtimes/navly-runtime/scripts/validate-milestone-b.sh
bash bridges/openclaw-host-bridge/scripts/validate-milestone-b.sh
