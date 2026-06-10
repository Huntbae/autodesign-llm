#!/usr/bin/env bash
# 문서 산출물 재생성 — 구성도(PNG) + Word(.docx) + 요약(PPTX)
set -euo pipefail
cd "$(dirname "$0")/.."
PYBIN=".venv/bin/python"; [ -x "$PYBIN" ] || PYBIN="python3"
echo "[1/3] 시스템 구성도 PNG"; "$PYBIN" assets/make_diagrams.py
echo "[2/3] Word 문서";        "$PYBIN" assets/md_to_docx.py
echo "[3/3] 요약 PPTX";        "$PYBIN" assets/build_pptx.py
echo "완료 → word/, assets/*.png, AutoDesign-LLM_요약.pptx"
