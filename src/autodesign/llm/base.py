"""LLM 백엔드 계약(인터페이스).

세 배포 버전(v1 로컬 / v2 하이브리드 / v3 클라우드)이 모두 이 Protocol을 구현한다.
코어는 어떤 백엔드인지 모른 채 동작 → 이식성 확보. (docs/02-DEV-PROCESS §2)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Protocol, runtime_checkable

from ..spec import DesignSpec


@dataclass
class GenerationResult:
    """LLM이 산출한 설계 파라미터(+근거 메모)."""
    params: dict                 # 형상 생성기에 넣을 파라미터 (예: thickness_mm 등)
    rationale: str = ""          # 사전 검토/결정 근거 (P3에서 RAG 인용으로 강화)
    raw: str = ""                # 원본 응답(디버그)


@runtime_checkable
class LLMClient(Protocol):
    """모든 LLM 백엔드의 공통 계약."""

    def parse_spec(self, natural_language: str) -> DesignSpec:
        """① 자연어 → 구조화된 DesignSpec."""
        ...

    def propose(self, spec: DesignSpec) -> GenerationResult:
        """④ 설계명세 → 초기 형상 파라미터 제안."""
        ...

    def correct(self, spec: DesignSpec, prev_params: dict, feedback: str) -> GenerationResult:
        """⑥ 검증 실패 피드백 → 수정된 파라미터(자기교정)."""
        ...
