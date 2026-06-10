#!/usr/bin/env bash
# GitHub 공개 저장소 생성 + push (1회). 터미널에서 직접 실행하세요.
#   ./scripts/publish.sh            # public, Huntbae/autodesign-llm
#   ./scripts/publish.sh myname myrepo private
set -euo pipefail
cd "$(dirname "$0")/.."
export PATH="/opt/homebrew/bin:$PATH"

OWNER="${1:-Huntbae}"
REPO="${2:-autodesign-llm}"
VIS="${3:-public}"        # public | private

command -v gh >/dev/null || { echo "gh 미설치 → brew install gh"; exit 1; }

# 1) 인증(미인증 시 브라우저 로그인 — 이 터미널에서 진행)
if ! gh auth status >/dev/null 2>&1; then
  echo "▶ GitHub 로그인(브라우저)이 필요합니다…"
  gh auth login --hostname github.com --git-protocol https --web
fi

# 2) main 브랜치 보장
git branch -M main 2>/dev/null || true

# 3) 저장소 생성 + push (이미 있으면 remote 연결 후 push)
if gh repo view "$OWNER/$REPO" >/dev/null 2>&1; then
  echo "▶ 기존 저장소에 push: $OWNER/$REPO"
  git remote get-url origin >/dev/null 2>&1 || git remote add origin "https://github.com/$OWNER/$REPO.git"
  git push -u origin main
else
  echo "▶ 새 저장소 생성($VIS) + push: $OWNER/$REPO"
  gh repo create "$OWNER/$REPO" "--$VIS" --source=. --remote=origin --push \
    --description "자연어로 자동차 부품을 설계하고 이론·표준 근거로 검증하는 LLM 시스템 (FreeCAD/FEM/Hermes)"
fi

echo "✅ 완료 → $(gh repo view "$OWNER/$REPO" --json url -q .url)"
