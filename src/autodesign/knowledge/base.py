"""지식 청크 + 검색기 계약."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Protocol, Tuple, runtime_checkable


@dataclass
class Chunk:
    id: str
    text: str
    source: str                       # 출처(검증 추적용) — 인용에 사용
    category: str = "general"         # material | design_rule | standard | paper ...
    meta: Dict = field(default_factory=dict)


@runtime_checkable
class Retriever(Protocol):
    def search(self, query: str, k: int = 5) -> List[Tuple[Chunk, float]]:
        """질의에 대해 (청크, 점수) 상위 k개 반환."""
        ...
