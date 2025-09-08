#!/usr/bin/env bash
# Run pytest suite with coverage, preferring `uv` if available.
set -euo pipefail

echo "Running tests via $(command -v uv >/dev/null 2>&1 && echo 'uv' || echo 'python')..."

if command -v uv >/dev/null 2>&1; then
  uv run pytest tests/ -v --cov=src/dynadock --cov-report=term-missing --cov-report=html
else
  # Ensure pytest is available; install minimal deps if necessary
  python3 - <<'PY'
import sys, importlib.util, subprocess
mods = ["pytest", "pytest-cov", "requests", "pytest-timeout"]
missing = [m for m in mods if importlib.util.find_spec(m) is None]
if missing:
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", *missing], check=True)
PY
  python3 -m pytest tests/ -v --cov=src/dynadock --cov-report=term-missing --cov-report=html
fi
