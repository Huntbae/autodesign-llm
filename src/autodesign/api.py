"""Phase 7 — 통합 고수준 API (제품 파사드).

자연어 한 줄로 전체 파이프라인을 실행: 파싱 → 사전검토(RAG) → 생성·검증·자기교정
→ (선택) 경량화 → (선택) 보고서. LLM/솔버/검색기를 주입해 v1/v2/v3 전환 가능.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional

from .knowledge import KnowledgeBase, build_prereview
from .llm import MockLLM
from .llm.base import LLMClient
from .optimization import OptimizationResult, lightweight
from .orchestrator import DesignLoop, LoopResult
from .reporting import build_report
from .spec import DesignSpec


@dataclass
class DesignOutcome:
    spec: DesignSpec
    prereview: str
    loop: LoopResult
    optimization: Optional[OptimizationResult] = None
    report_paths: Dict[str, str] = field(default_factory=dict)

    @property
    def converged(self) -> bool:
        return self.loop.converged

    def summary(self) -> str:
        parts = [self.prereview, "", self.loop.report()]
        if self.optimization:
            parts += ["", self.optimization.report()]
        if self.report_paths:
            parts += ["", "보고서: " + ", ".join(f"{k}={v}" for k, v in self.report_paths.items())]
        return "\n".join(parts)


def design_part(request: str, *, llm: Optional[LLMClient] = None,
                kb: Optional[KnowledgeBase] = None, optimize: bool = False,
                report: bool = False, out_dir: str = ".",
                max_iter: int = 8) -> DesignOutcome:
    """구조 부품 설계 파이프라인 전체 실행."""
    llm = llm or MockLLM()
    kb = kb or KnowledgeBase.load_default()

    spec = llm.parse_spec(request)
    prereview = build_prereview(spec, kb)
    loop_result = DesignLoop(llm, max_iter=max_iter).run(spec)

    outcome = DesignOutcome(spec=spec, prereview=prereview, loop=loop_result)

    if optimize and loop_result.converged and loop_result.model is not None:
        outcome.optimization = lightweight(spec, loop_result.model)

    if report:
        # 경량화 결과가 있으면 그 모델을 최종으로 반영
        if outcome.optimization is not None:
            loop_result.model = outcome.optimization.optimized
        outcome.report_paths = build_report(loop_result, prereview, out_dir=out_dir)

    return outcome


def design_exterior(request: str, *, speed_ms: float = 30.0):
    """외형(공력) 개념 설계 파이프라인. 별도 모듈(exterior) 위임."""
    from .exterior import ExteriorLoop, MockConceptGenerator
    concept = MockConceptGenerator().generate(request)
    return concept, ExteriorLoop(speed_ms=speed_ms).run(concept)
