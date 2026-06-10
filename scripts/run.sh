#!/usr/bin/env bash
# CLI 실행 래퍼 — 가상환경 + PYTHONPATH 자동 처리
# 예: ./scripts/run.sh --backend hermes --trace "엔진 브래킷, 5kN, AlSi10Mg, 안전계수 2.0, 피로"
set -euo pipefail
cd "$(dirname "$0")/.."
PYBIN=".venv/bin/python"; [ -x "$PYBIN" ] || PYBIN="python3"
PYTHONPATH=src "$PYBIN" -m autodesign.cli "$@"
