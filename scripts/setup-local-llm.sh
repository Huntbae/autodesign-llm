#!/usr/bin/env bash
# 로컬 LLM 1회 셋업 — Ollama 설치 + 코드특화 모델 다운로드.
# 100% 로컬: 클라우드/API 키 불필요, 설계 데이터 외부 전송 없음.
#   사용: ./scripts/setup-local-llm.sh
#   모델 변경: OLLAMA_MODEL=qwen2.5-coder:32b ./scripts/setup-local-llm.sh
set -euo pipefail
cd "$(dirname "$0")/.."

MODEL="${OLLAMA_MODEL:-qwen2.5-coder:7b}"   # 기본: 코드특화 7B(약 4.7GB). 품질↑ 원하면 32B
HOST="${OLLAMA_HOST:-http://localhost:11434}"

echo "[1/3] Ollama 설치 확인"
if command -v ollama >/dev/null 2>&1; then
  echo "  이미 설치됨: $(ollama --version 2>/dev/null | head -1)"
else
  case "$(uname -s)" in
    Darwin)
      if command -v brew >/dev/null 2>&1; then
        echo "  Homebrew로 설치"; brew install ollama
      else
        echo "  ✗ Homebrew 없음 → https://ollama.com/download 에서 설치 후 다시 실행" >&2
        exit 1
      fi ;;
    Linux)
      echo "  공식 설치 스크립트 실행"; curl -fsSL https://ollama.com/install.sh | sh ;;
    *)
      echo "  ✗ 지원되지 않는 OS → https://ollama.com/download" >&2; exit 1 ;;
  esac
fi

echo "[2/3] Ollama 서버 기동"
if curl -sf "${HOST}/api/tags" >/dev/null 2>&1; then
  echo "  이미 동작 중 (${HOST})"
else
  ollama serve >/tmp/ollama.log 2>&1 &
  for _ in $(seq 1 30); do
    curl -sf "${HOST}/api/tags" >/dev/null 2>&1 && break; sleep 1
  done
  curl -sf "${HOST}/api/tags" >/dev/null 2>&1 \
    && echo "  시작됨 (${HOST})" \
    || { echo "  ✗ 서버 기동 실패. 로그: /tmp/ollama.log" >&2; exit 1; }
fi

echo "[3/3] 모델 다운로드: ${MODEL} (최초 1회, 수 GB)"
ollama pull "${MODEL}"

cat <<EOF

✅ 로컬 LLM 셋업 완료 (모델: ${MODEL})
  실행:  ./scripts/run-local.sh --report --trace "엔진 브래킷, 5kN, AlSi10Mg, 안전계수 2.0, 피로"
EOF
