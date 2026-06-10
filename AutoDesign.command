#!/usr/bin/env bash
# ▶ 더블클릭 실행 런처 (macOS) — 오프라인 데모
#   자연어 → 설계·검증·자기교정 → 경량화 → 보고서, 끝나면 보고서를 자동으로 엽니다.
#   ※ 인터넷/LLM 설치 불필요 (항상 동작).  로컬 LLM으로 돌리려면 AutoDesign-LocalLLM.command 사용.
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"
clear
echo "================================================"
echo "   AutoDesign-LLM  ▶  실행 (오프라인 데모)"
echo "================================================"

# 1) 최초 1회 환경 자동 준비
if [ ! -x ".venv/bin/python" ]; then
  echo "[준비] 최초 환경 설정 중... (1~2분, 한 번만)"
  bash scripts/setup.sh
fi

# 2) 파이프라인 실행 (구조 부품: 경량화 + 보고서)
echo "[실행] 엔진 마운트 브래킷 설계·검증·경량화..."
echo
./scripts/run.sh --optimize --report

# 3) 결과 보고서 자동 열기 (macOS)
if command -v open >/dev/null 2>&1 && [ -f review_report.html ]; then
  open review_report.html
fi

echo
echo "✅ 완료. 보고서: $DIR/review_report.html (.pdf)"
echo "   (이 창은 닫으셔도 됩니다)"
