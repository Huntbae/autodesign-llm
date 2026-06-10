#!/usr/bin/env bash
# ▶ 더블클릭 실행 런처 (macOS) — 100% 로컬 LLM(Ollama)
#   Ollama·모델·서버 준비를 자동으로 끝낸 뒤, 자연어 요구로 설계를 실행합니다.
#   설계 데이터가 외부로 나가지 않습니다(IP 보안).  최초 실행은 모델 다운로드로 시간이 걸립니다.
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"
clear
echo "================================================"
echo "   AutoDesign-LLM  ▶  실행 (로컬 LLM / Ollama)"
echo "================================================"

REQ="엔진 마운트 브래킷, 수직 5kN, 재질 AlSi10Mg, 안전계수 2.0, 1차 고유진동수 150Hz, 피로 내구"

# 1) 파이썬 환경
if [ ! -x ".venv/bin/python" ]; then
  echo "[준비] 파이썬 환경 설정 중..."
  bash scripts/setup.sh
fi

# 2) Ollama 미설치면 1회 셋업(설치+모델 다운로드)
if ! command -v ollama >/dev/null 2>&1; then
  echo "[준비] Ollama·모델 최초 설치 중... (수 분 소요)"
  bash scripts/setup-local-llm.sh
fi

# 3) 로컬 LLM으로 실행 (서버/모델 누락분은 run-local.sh가 자동 보충)
echo "[실행] \"$REQ\""
echo
./scripts/run-local.sh --report --trace "$REQ"

# 4) 보고서 자동 열기
if command -v open >/dev/null 2>&1 && [ -f review_report.html ]; then
  open review_report.html
fi

echo
echo "✅ 완료. 보고서: $DIR/review_report.html (.pdf)"
echo "   (이 창은 닫으셔도 됩니다)"
