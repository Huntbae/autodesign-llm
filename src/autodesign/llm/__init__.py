"""② LLM 백엔드 추상화. base.LLMClient 계약 뒤에 mock/cloud/local을 숨긴다."""
from .base import LLMClient, GenerationResult
from .mock_backend import MockLLM
from .factory import get_llm
from .observe import ObservedLLM, UsageRecorder

__all__ = ["LLMClient", "GenerationResult", "MockLLM", "get_llm",
           "ObservedLLM", "UsageRecorder"]
