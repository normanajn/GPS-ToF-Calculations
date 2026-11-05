#!/usr/bin/env bash
# Run gps-tof from the project virtual environment, creating/updating it first.
set -euo pipefail
cd "$(dirname "$0")"
if [ ! -x venv/bin/gps-tof ]; then
    python3 -m venv venv
    ./venv/bin/python -m pip install --upgrade pip >/dev/null
    ./venv/bin/python -m pip install -q -e .
else
    ./venv/bin/python -m pip install -q -e . >/dev/null
fi
exec ./venv/bin/gps-tof "$@"
