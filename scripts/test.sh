#!/usr/bin/env bash
# 전체 테스트
set -euo pipefail
cd "$(dirname "$0")/.."
PYBIN=".venv/bin/python"; [ -x "$PYBIN" ] || PYBIN="python3"
PYTHONPATH=src "$PYBIN" -m pytest tests/ -q "$@"
