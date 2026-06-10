"""생성 → 검증 → 자기교정 루프 (시스템의 심장).

원칙(docs/02-DEV-PROCESS): 검증 게이트가 통과를 만들 때까지 LLM이 교정.
LLM 백엔드는 주입(DI)받으므로 mock/local/cloud 무관하게 동작.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from ..geometry.bracket import BracketModel, build_bracket
from ..llm.base import LLMClient, GenerationResult
from ..spec import DesignSpec
from ..validation import ValidationResult, run_validation


@dataclass
class Iteration:
    n: int
    params: dict
    rationale: str
    result: ValidationResult


@dataclass
class LoopResult:
    spec: DesignSpec
    iterations: List[Iteration] = field(default_factory=list)
    model: Optional[BracketModel] = None
    converged: bool = False

    @property
    def n_iter(self) -> int:
        return len(self.iterations)

    def report(self) -> str:
        lines = [f"=== 설계 루프 리포트 ({self.spec.part_type}) ==="]
        for it in self.iterations:
            lines.append(f"\n[반복 {it.n}] params={it.params}")
            lines.append(f"  근거: {it.rationale}")
            lines.append(it.result.summary())
        status = "✅ 수렴(모든 검증 통과)" if self.converged else "❌ 미수렴(최대 반복 도달)"
        lines.append(f"\n결과: {status}  (반복 {self.n_iter}회)")
        if self.model:
            lines.append(
                f"최종: 두께 {self.model.thickness_mm:.2f}mm, "
                f"질량 {self.model.mass_kg()*1000:.0f}g, "
                f"SF {self.model.safety_factor():.2f}"
            )
        return "\n".join(lines)


class DesignLoop:
    def __init__(self, llm: LLMClient, max_iter: int = 6):
        self.llm = llm
        self.max_iter = max_iter

    def run(self, spec: DesignSpec) -> LoopResult:
        errs = spec.validate()
        if errs:
            raise ValueError("설계명세 오류: " + "; ".join(errs))

        out = LoopResult(spec=spec)
        gen: GenerationResult = self.llm.propose(spec)

        for n in range(1, self.max_iter + 1):
            model = build_bracket(spec, gen.params)
            result = run_validation(model, spec)
            out.iterations.append(Iteration(n, dict(gen.params), gen.rationale, result))
            out.model = model

            if result.passed:
                out.converged = True
                break

            # 자기교정: 검증 피드백 → LLM이 파라미터 수정
            gen = self.llm.correct(spec, gen.params, result.feedback())

        return out
