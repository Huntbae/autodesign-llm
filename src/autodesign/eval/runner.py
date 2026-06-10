"""평가 러너 — 임의 LLMClient를 평가셋으로 채점(파싱 정확도 + 루프 수렴).

오프라인(mock)에서 결정적. cloud/local은 키/서비스 있을 때 동일하게 채점.
실 백엔드의 네트워크 예외는 케이스 실패로 집계(평가 자체는 멈추지 않음).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from ..api import design_part
from ..llm.base import LLMClient
from .cases import EVAL_CASES, EvalCase


@dataclass
class CaseResult:
    name: str
    parse_ok: bool
    loop_converged: bool
    final_sf: Optional[float]
    sf_met: bool
    error: str = ""

    @property
    def passed(self) -> bool:
        return self.parse_ok and self.loop_converged and self.sf_met


@dataclass
class EvalReport:
    results: List[CaseResult] = field(default_factory=list)

    @property
    def parse_accuracy(self) -> float:
        return _frac(r.parse_ok for r in self.results)

    @property
    def loop_pass_rate(self) -> float:
        return _frac(r.loop_converged and r.sf_met for r in self.results)

    @property
    def score(self) -> float:
        return _frac(r.passed for r in self.results)

    def summary(self) -> str:
        lines = ["── 평가 리포트 ──"]
        for r in self.results:
            mark = "✅" if r.passed else "❌"
            sf = f"{r.final_sf:.2f}" if r.final_sf is not None else "-"
            lines.append(f"  {mark} {r.name:28s} parse={r.parse_ok} "
                         f"conv={r.loop_converged} SF={sf}"
                         + (f"  err={r.error}" if r.error else ""))
        lines.append(f"\n파싱 정확도 {self.parse_accuracy:.0%} · "
                     f"루프 통과율 {self.loop_pass_rate:.0%} · "
                     f"종합 {self.score:.0%} ({len(self.results)}건)")
        return "\n".join(lines)


def _frac(it) -> float:
    items = list(it)
    return sum(1 for x in items if x) / len(items) if items else 0.0


def _check_parse(spec, case: EvalCase) -> bool:
    ok = spec.material == case.material
    ok = ok and abs(spec.targets.safety_factor - case.safety_factor) < 1e-6
    ok = ok and ((spec.targets.min_fatigue_cycles is not None) == case.has_fatigue)
    return ok


def run_eval(llm: LLMClient, cases: Optional[List[EvalCase]] = None,
             run_loop: bool = True) -> EvalReport:
    cases = cases or EVAL_CASES
    report = EvalReport()
    for case in cases:
        try:
            spec = llm.parse_spec(case.request)
            parse_ok = _check_parse(spec, case)
            converged = False
            final_sf = None
            sf_met = False
            if run_loop:
                outcome = design_part(case.request, llm=llm)
                converged = outcome.converged
                if outcome.loop.model is not None:
                    final_sf = outcome.loop.model.safety_factor()
                    sf_met = final_sf >= case.safety_factor - 1e-6
            else:
                sf_met = True
            report.results.append(CaseResult(case.name, parse_ok, converged, final_sf, sf_met))
        except Exception as e:  # 실 백엔드 네트워크/형식 오류도 실패로 집계
            report.results.append(CaseResult(case.name, False, False, None, False, str(e)[:80]))
    return report
