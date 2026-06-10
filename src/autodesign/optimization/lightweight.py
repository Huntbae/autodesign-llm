"""경량화 최적화 (Phase 5).

목표: 모든 검증 게이트(강도·피로·DFM·모달)를 만족하면서 질량 최소화.
방법(현재): 두께 × 포켓비율 파라미터 스윕(제약 만족 중 최소 질량 선택).
   - 두께↓ → 질량↓이나 응력↑(강도/피로 제약)
   - 포켓↑ → 질량↓이나 유효폭↓로 응력↑ (저응력부 살빼기의 보수적 모델)
※ 실제 위상최적화(SIMP/BESO + FEM)로 교체 예정. 본 구현은 워크플로 시연.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from ..geometry.bracket import BracketModel, build_bracket
from ..spec import DesignSpec
from ..validation import run_validation
from ..validation.structural import StructuralSolver


@dataclass
class OptimizationResult:
    baseline: BracketModel
    optimized: BracketModel
    evaluations: int
    feasible_count: int

    @property
    def mass_reduction(self) -> float:
        m0 = self.baseline.mass_kg()
        return (m0 - self.optimized.mass_kg()) / m0 if m0 > 0 else 0.0

    def report(self) -> str:
        r = self.mass_reduction * 100
        b, o = self.baseline, self.optimized
        return (
            "── 경량화 최적화 리포트 ──\n"
            f"  baseline : 두께 {b.thickness_mm:.2f}mm, 포켓 {b.pocket_fraction:.0%}, "
            f"질량 {b.mass_kg()*1000:.0f}g, SF {b.safety_factor():.2f}\n"
            f"  optimized: 두께 {o.thickness_mm:.2f}mm, 포켓 {o.pocket_fraction:.0%}, "
            f"질량 {o.mass_kg()*1000:.0f}g, SF {o.safety_factor():.2f}\n"
            f"  → 질량 {r:.1f}% 감소 (평가 {self.evaluations}회, 가능해 {self.feasible_count}개)"
        )


def _frange(lo: float, hi: float, step: float) -> List[float]:
    out, v = [], lo
    while v <= hi + 1e-9:
        out.append(round(v, 3)); v += step
    return out


def lightweight(spec: DesignSpec, baseline: BracketModel,
                solver: Optional[StructuralSolver] = None,
                t_min: float = 2.0, pocket_max: float = 0.45) -> OptimizationResult:
    """baseline 대비 질량 최소 가능해를 파라미터 스윕으로 탐색."""
    base_params = dict(thickness_mm=baseline.thickness_mm, fillet_mm=baseline.fillet_mm,
                       bolt_dia_mm=baseline.bolt_dia_mm, n_bolts=baseline.n_bolts)
    best: Optional[BracketModel] = None
    evals = feasible = 0

    t_hi = max(baseline.thickness_mm * 1.3, baseline.thickness_mm + 2)
    for t in _frange(t_min, t_hi, 0.5):
        for p in _frange(0.0, pocket_max, 0.05):
            params = dict(base_params, thickness_mm=t, pocket_fraction=p)
            model = build_bracket(spec, params)
            res = run_validation(model, spec, solver=solver)
            evals += 1
            if res.passed:
                feasible += 1
                if best is None or model.mass_kg() < best.mass_kg():
                    best = model

    if best is None:           # 가능해 없음 → baseline 유지
        best = baseline
    return OptimizationResult(baseline=baseline, optimized=best,
                              evaluations=evals, feasible_count=feasible)
