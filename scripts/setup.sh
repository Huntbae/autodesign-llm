#!/usr/bin/env bash
# 맥북프로 1회 셋업 — 가상환경 + 의존성 + 스모크 테스트
set -euo pipefail
cd "$(dirname "$0")/.."

echo "[1/4] 가상환경(.venv) 생성"
python3 -m venv .venv

echo "[2/4] pip 업그레이드 + 코어(dev) 설치"
.venv/bin/python -m pip install --upgrade pip >/dev/null
.venv/bin/pip install -e ".[dev]"

echo "[3/4] 문서 생성 도구(선택) 설치 — 다이어그램/Word/PPTX/PDF"
.venv/bin/pip install matplotlib python-docx python-pptx reportlab >/dev/null || \
  echo "  (문서 도구 설치 실패 — 코드 동작에는 영향 없음)"

echo "[4/4] 스모크 테스트"
PYTHONPATH=src .venv/bin/python -m pytest tests/ -q

cat <<'EOF'

✅ 셋업 완료.
  활성화:  source .venv/bin/activate
  데모:    ./scripts/run.sh --optimize --report
  실 LLM:  ./scripts/run.sh --backend hermes --trace "엔진 브래킷, 5kN, AlSi10Mg, 안전계수 2.0, 피로"
  (Claude를 쓰려면  pip install anthropic  + export ANTHROPIC_API_KEY=...)
EOF
