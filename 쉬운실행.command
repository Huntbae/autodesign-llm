#!/usr/bin/env bash
# ▶ 더블클릭하면 시작! (초등학생도 OK)
#   질문 2개에 답하면 컴퓨터가 자동차(또는 부품)를 만들어서 보여줍니다.
set -uo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"
clear
echo ""
echo "  ╔══════════════════════════════════════╗"
echo "  ║   🚗  말로 만드는 자동차 공장  🔧      ║"
echo "  ╚══════════════════════════════════════╝"
echo ""

# ── 0) 컴퓨터 준비(처음 한 번만, 자동) ──
if [ ! -x ".venv/bin/python" ]; then
  echo "  ⏳ 처음이라 준비 중이에요... (1~2분, 한 번만)"
  bash scripts/setup.sh >/dev/null 2>&1 || bash scripts/setup.sh
  echo "  ✅ 준비 끝!"
  echo ""
fi

# ── 똑똑한 두뇌(로컬 LLM) 자동 선택: 있으면 쓰고, 없으면 기본 두뇌 ──
BACKEND="mock"
HOST="${OLLAMA_HOST:-http://localhost:11434}"
if command -v ollama >/dev/null 2>&1; then
  curl -sf "${HOST}/api/tags" >/dev/null 2>&1 || { ollama serve >/tmp/ollama.log 2>&1 & sleep 3; }
  if curl -sf "${HOST}/api/tags" >/dev/null 2>&1; then
    BACKEND="local"
    export OLLAMA_HOST="$HOST"
  fi
fi
if [ "$BACKEND" = "local" ]; then
  echo "  🧠 인공지능 두뇌: 내 컴퓨터의 AI (Ollama)"
else
  echo "  🧠 인공지능 두뇌: 기본 모드 (AI 설치는 어른과 함께: ./scripts/setup-local-llm.sh)"
fi
echo ""

# ── 1) 무엇을 만들까? ──
echo "  ① 무엇을 만들까요? 숫자를 누르고 Enter!"
echo "     1) 🚗 자동차 디자인"
echo "     2) 🔩 자동차 부품 (브래킷)"
printf "     👉 번호: "
read -r CHOICE
CHOICE="${CHOICE:-1}"
echo ""

# ── 2) 말로 설명하기 ──
if [ "$CHOICE" = "2" ]; then
  DEFAULT="엔진 마운트 브래킷, 수직 5kN, 재질 AlSi10Mg, 안전계수 2.0, 피로 내구"
  echo "  ② 어떤 부품인지 말해 주세요 (그냥 Enter = 예시로 만들기)"
else
  DEFAULT="낮은 스포츠 쿠페, 패스트백, 큰 휠"
  echo "  ② 어떤 자동차인지 말해 주세요 (그냥 Enter = 멋진 스포츠카)"
  echo "     예) 높은 SUV / 미드십 슈퍼카, 매우 낮고 와이드 / 세단, 노치백"
fi
printf "     👉 설명: "
read -r WORDS
WORDS="${WORDS:-$DEFAULT}"
echo ""
echo "  🏭 만드는 중... 조금만 기다려 주세요!"
echo "  ──────────────────────────────────────"

# ── 3) 실행 ──
if [ "$CHOICE" = "2" ]; then
  PYTHONPATH=src .venv/bin/python -m autodesign.cli --backend "$BACKEND" --optimize --report "$WORDS"
  RESULT_HTML="review_report.html"
  if command -v open >/dev/null 2>&1 && [ -f "$RESULT_HTML" ]; then open "$RESULT_HTML"; fi
  echo ""
  echo "  🎉 완성! 부품 보고서가 열렸어요: $DIR/$RESULT_HTML"
else
  PYTHONPATH=src .venv/bin/python -m autodesign.cli --backend "$BACKEND" --exterior "$WORDS"
  OBJ="car_body_concept.obj"
  if [ -f "$OBJ" ] && command -v qlmanage >/dev/null 2>&1; then
    qlmanage -p "$OBJ" >/dev/null 2>&1 &       # 맥의 3D 미리보기로 띄우기
  elif [ -f "$OBJ" ] && command -v open >/dev/null 2>&1; then
    open -R "$OBJ"                              # 안 되면 파일 위치 보여주기
  fi
  echo ""
  echo "  🎉 완성! 자동차 3D 파일: $DIR/$OBJ"
  echo "     (Finder에서 파일을 누르고 스페이스바 = 3D로 빙글빙글 보기)"
fi
echo ""
echo "  또 만들고 싶으면 이 아이콘을 다시 더블클릭하세요! 👋"
