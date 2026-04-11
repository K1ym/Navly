#!/usr/bin/env bash
set -euo pipefail

python3 scripts/full_phase1_acceptance_suite_manifest.py > /dev/null
bash scripts/validate-first-usable-alpha-smoke.sh
bash scripts/validate-remaining-phase1-live-transport.sh
python3 -m unittest discover -s platforms/data-platform/tests -p 'test_*.py'
