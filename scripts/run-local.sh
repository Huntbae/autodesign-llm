#!/usr/bin/env bash
# 로컬 LLM(Ollama)으로 실행 — 100% 로컬, 클라우드/API 키 불필요.
# 누락된 것(venv·서버·모델)은 자동으로 채운 뒤 CLI를 실행한다.
#   예: ./scripts/run-local.sh --report --trace "엔진 브래킷, 5kN, AlSi10Mg, 안전계수 2.0, 피로"
#       ./scripts/run-local.sh --optimize --report          # 경량화+보고서
#       OLLAMA_MODEL=qwen2.5-coder:32b ./scripts/run-local.sh ...   # 모델 변경
set -euo pipefail
cd "$(dirname "$0")/.."

MODEL="${OLLAMA_MODEL:-qwen2.5-coder:7b}"
HOST="${OLLAMA_HOST:-http://localhost:11434}"

# 1) 파이썬 환경
if [ ! -x ".venv/bin/python" ]; then
  echo "[run-local] .venv 없음 → scripts/setup.sh 실행"
  bash scripts/setup.sh
fi

# 2) Ollama 설치 확인
if ! command -v ollama >/dev/null 2>&1; then
  echo "✗ Ollama 미설치. 먼저 1회 셋업하세요:" >&2
  echo "    ./scripts/setup-local-llm.sh" >&2
  exit 1
fi

# 3) 서버 기동 확인(없으면 시작)
if ! curl -sf "${HOST}/api/tags" >/dev/null 2>&1; then
  echo "[run-local] ollama 서버 시작..."
  ollama serve >/tmp/ollama.log 2>&1 &
  for _ in $(seq 1 30); do
    curl -sf "${HOST}/api/tags" >/dev/null 2>&1 && break; sleep 1
  done
fi
if ! curl -sf "${HOST}/api/tags" >/dev/null 2>&1; then
  echo "✗ Ollama 서버(${HOST})에 연결 불가. 로그: /tmp/ollama.log" >&2
  exit 1
fi

# 4) 모델 확인(없으면 pull)
if ! ollama list 2>/dev/null | grep -q "${MODEL%%:*}"; then
  echo "[run-local] 모델 ${MODEL} 다운로드(최초 1회)..."
  ollama pull "${MODEL}"
fi

# 5) 실행 (--backend local 고정)
export OLLAMA_HOST="${HOST}" OLLAMA_MODEL="${MODEL}"
echo "[run-local] backend=local  model=${MODEL}  host=${HOST}"
PYTHONPATH=src .venv/bin/python -m autodesign.cli --backend local "$@"
