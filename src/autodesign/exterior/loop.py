"""외형 개념→공력→교정 루프. Cd 목표를 만족할 때까지 형상지표를 조정.

구조 루프(orchestrator)와 동일한 패턴 — 검증 축만 공력(Cd)으로 교체.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from .aero import AeroResult, AeroSolver, AnalyticDragSolver
from .concept import ConceptSpec, MockConceptGenerator


@dataclass
class ExteriorIteration:
    n: int
    streamline: float
    aero: AeroResult
    passed: bool


@dataclass
class ExteriorResult:
    concept: Optional[ConceptSpec] = None
    iterations: List[ExteriorIteration] = field(default_factory=list)
    converged: bool = False

    @property
    def n_iter(self) -> int:
        return len(self.iterations)

    def report(self) -> str:
        lines = ["── 외형(공력) 루프 리포트 ──"]
        for it in self.iterations:
            mark = "✅" if it.passed else "❌"
            lines.append(f"  [반복 {it.n}] streamline={it.streamline:.2f}  "
                         f"Cd={it.aero.cd:.3f}  항력={it.aero.drag_N:.0f}N  {mark}")
        status = "수렴(Cd 목표 달성)" if self.converged else "미수렴"
        lines.append(f"결과: {status} (반복 {self.n_iter}회)")
        return "\n".join(lines)


class ExteriorLoop:
    def __init__(self, generator: Optional[MockConceptGenerator] = None,
                 solver: Optional[AeroSolver] = None, max_iter: int = 8,
                 speed_ms: float = 30.0):
        self.gen = generator or MockConceptGenerator()
        self.solver = solver or AnalyticDragSolver()
        self.max_iter = max_iter
        self.speed_ms = speed_ms

    def run(self, concept: ConceptSpec) -> ExteriorResult:
        out = ExteriorResult(concept=concept)
        cur = concept
        for n in range(1, self.max_iter + 1):
            aero = self.solver.solve(cur, self.speed_ms)
            passed = aero.cd <= cur.target_cd
            out.iterations.append(ExteriorIteration(n, cur.streamline, aero, passed))
            out.concept = cur
            if passed:
                out.converged = True
                break
            cur = self.gen.restyle(cur, delta_streamline=0.1)   # 교정: 더 매끈하게
            if cur.streamline >= 1.0 and not passed:
                # 더 이상 개선 불가 → 한 번 더 평가 후 종료
                aero = self.solver.solve(cur, self.speed_ms)
                passed = aero.cd <= cur.target_cd
                out.iterations.append(ExteriorIteration(n + 1, cur.streamline, aero, passed))
                out.converged = passed
                break
        return out
