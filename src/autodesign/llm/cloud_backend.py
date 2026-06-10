"""클라우드 백엔드 — Claude(Anthropic) 구현. (배포 v3)

claude-api 사양: 모델 claude-opus-4-8, adaptive thinking + effort,
구조화 출력 output_config.format(json_schema). temperature/budget_tokens 미사용.
anthropic SDK는 지연 임포트(미설치/오프라인 테스트 시 transport 주입으로 대체).
"""
from __future__ import annotations

import json
from typing import Optional

from .json_llm import JsonLLMBase

MODEL = "claude-opus-4-8"


class CloudLLM(JsonLLMBase):
    def __init__(self, *, model: str = MODEL, effort: str = "high",
                 client=None, max_tokens: int = 4000, **kw):
        super().__init__(**kw)
        self.model = model
        self.effort = effort
        self.max_tokens = max_tokens
        self._client = client  # 주입 가능(테스트). None이면 지연 생성.

    def _anthropic(self):
        if self._client is None:
            try:
                import anthropic  # 지연 임포트
            except ImportError as e:
                raise RuntimeError(
                    "Claude 백엔드를 쓰려면 `pip install anthropic` 후 "
                    "ANTHROPIC_API_KEY를 설정하세요. (오프라인은 --backend mock)"
                ) from e
            self._client = anthropic.Anthropic()
        return self._client

    def _message(self, system: str, user: str, output_config: Optional[dict] = None) -> str:
        # 시스템 프롬프트는 안정적 prefix → 프롬프트 캐싱(cache_control)
        kwargs = dict(
            model=self.model,
            max_tokens=self.max_tokens,
            thinking={"type": "adaptive"},
            output_config={"effort": self.effort},
            system=[{"type": "text", "text": system,
                     "cache_control": {"type": "ephemeral"}}],
            messages=[{"role": "user", "content": user}],
        )
        if output_config:
            kwargs["output_config"] = {**kwargs["output_config"], **output_config}
        resp = self._anthropic().messages.create(**kwargs)
        return next((b.text for b in resp.content if getattr(b, "type", "") == "text"), "")

    def _raw_json(self, system: str, user: str, schema: dict) -> str:
        # 구조화 출력 강제: 첫 텍스트 블록이 유효 JSON
        return self._message(system, user,
                             output_config={"format": {"type": "json_schema", "schema": schema}})

    def _raw_text(self, system: str, user: str) -> str:
        return self._message(system, user)
