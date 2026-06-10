"""로컬 백엔드 — Ollama 구현. (배포 v1 / v2 추론부)

Ollama HTTP(/api/chat)를 urllib로 호출(추가 의존성 없음). 구조화 출력은
`format`에 JSON 스키마를 전달. 코드특화 모델(qwen2.5-coder 등) 권장.
오프라인 테스트는 transport 주입으로 대체.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request

from .json_llm import JsonLLMBase

DEFAULT_HOST = "http://localhost:11434"
DEFAULT_MODEL = "qwen2.5-coder:32b"


class LocalLLM(JsonLLMBase):
    def __init__(self, *, model: str = DEFAULT_MODEL, host: str = DEFAULT_HOST,
                 timeout: float = 120.0, **kw):
        super().__init__(**kw)
        self.model = model
        self.host = host.rstrip("/")
        self.timeout = timeout

    def _chat(self, system: str, user: str, fmt=None) -> str:
        payload = {
            "model": self.model,
            "stream": False,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "options": {"num_predict": 4000},
        }
        if fmt is not None:
            payload["format"] = fmt   # "json" 또는 JSON 스키마(dict)
        req = urllib.request.Request(
            f"{self.host}/api/chat",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                body = json.loads(r.read().decode("utf-8"))
        except urllib.error.URLError as e:
            raise RuntimeError(
                f"Ollama({self.host})에 연결할 수 없습니다: {e.reason}. "
                f"`ollama serve` 실행 후 `ollama pull {self.model}` 하세요. "
                "(오프라인은 --backend mock)"
            ) from e
        return body.get("message", {}).get("content", "")

    def _raw_json(self, system: str, user: str, schema: dict) -> str:
        # Ollama: format에 JSON 스키마 전달(구버전은 "json"으로 폴백)
        try:
            return self._chat(system, user, fmt=schema)
        except Exception:
            return self._chat(system, user, fmt="json")

    def _raw_text(self, system: str, user: str) -> str:
        return self._chat(system, user)
