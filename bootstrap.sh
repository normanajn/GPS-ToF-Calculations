#!/usr/bin/env bash
# Bootstrap gps-tof: create/refresh the Python virtual environment, install the package
# and its test dependencies, and run the test suite.  Linux and macOS.
set -euo pipefail
cd "$(dirname "$0")"
PY=${PYTHON:-python3}
if [ ! -d venv ]; then
    "$PY" -m venv venv
fi
./venv/bin/python -m pip install --upgrade pip >/dev/null
./venv/bin/python -m pip install -e '.[test]'
./venv/bin/python -m pytest -q
echo
echo "gps-tof is ready:  source venv/bin/activate && gps-tof -c config/nova.yaml"
