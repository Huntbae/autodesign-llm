"""Hermes 로컬 백엔드 — Ollama의 Hermes 3 모델을 함수호출 방식으로 구동. (배포 v1/v2)

LocalLLM(Ollama)을 상속하되, 구조화 출력을 Hermes 네이티브
`<tool_call>` 포맷으로 받아 파싱한다(Ollama가 content에 그대로 담는 경우 대비).
실패 시 Ollama `format`=schema(JSON 제약)로 폴백 → 견고함.
"""
from __future__ import annotations

from .hermes import build_tool_system, parse_tool_call
from .json_utils import extract_json
from .local_backend import LocalLLM

HERMES_MODEL = "hermes3"   # ollama pull hermes3 (8b/70b/405b)


class HermesLLM(LocalLLM):
    def __init__(self, *, model: str = HERMES_MODEL, **kw):
        super().__init__(model=model, **kw)

    def _raw_json(self, system: str, user: str, schema: dict) -> dict:
        # 1) Hermes 네이티브 함수호출 (ChatML tool_call)
        sys_aug = build_tool_system(system, schema)
        try:
            content = self._chat(sys_aug, user)        # format 미지정 → 모델 템플릿 사용
            data = parse_tool_call(content)
            if isinstance(data, dict) and data:
                return data
        except Exception:
            pass
        # 2) 폴백: Ollama format=schema 로 JSON 제약
        try:
            return extract_json(self._chat(system, user, fmt=schema))
        except Exception:
            return extract_json(self._chat(system, user, fmt="json"))
