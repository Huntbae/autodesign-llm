"""백엔드 팩토리 — mock/cloud/local 선택. (배포 v1/v2/v3 전환점)"""
from __future__ import annotations

import os

from .base import LLMClient
from .mock_backend import MockLLM


def get_llm(backend: str = "auto", **kw) -> LLMClient:
    """backend: 'mock' | 'cloud' | 'local' | 'auto'.

    auto: ANTHROPIC_API_KEY 있으면 cloud, OLLAMA_HOST 있으면 local, 아니면 mock.
    """
    if backend == "auto":
        # 안전한 기본은 mock(오프라인, 비용 0). 실 LLM은 명시 환경변수로만 선택.
        if os.getenv("NOUS_API_KEY"):
            backend = "hermes"
        elif os.getenv("ANTHROPIC_API_KEY"):
            backend = "cloud"
        elif os.getenv("OLLAMA_HOST"):
            backend = "ollama-hermes"
        else:
            backend = "mock"       # Hermes는 `--backend hermes`로 명시 선택

    if backend == "mock":
        return MockLLM()
    if backend == "cloud":
        from .cloud_backend import CloudLLM
        return CloudLLM(**kw)
    if backend in ("hermes", "nous"):
        # 사용자의 Hermes 에이전트(Nous 추론 API, OpenAI 호환)
        from .nous_backend import NousHermesLLM
        return NousHermesLLM(**kw)
    if backend in ("local", "ollama", "ollama-hermes"):
        host = os.getenv("OLLAMA_HOST")
        if host:
            kw.setdefault("host", host)
        if backend == "ollama-hermes":
            from .hermes_backend import HermesLLM
            model = os.getenv("HERMES_MODEL")
            if model:
                kw.setdefault("model", model)
            return HermesLLM(**kw)
        from .local_backend import LocalLLM
        model = os.getenv("OLLAMA_MODEL")
        if model:
            kw.setdefault("model", model)
        return LocalLLM(**kw)
    raise ValueError(f"알 수 없는 backend: {backend}")
