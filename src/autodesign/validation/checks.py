"""검증 체크 오케스트레이션.

게이트: 기하 유효성 → 구조 강도(솔버 주입) → DFM → 모달 → 질량.
- 구조 솔버는 주입(기본 AnalyticBendingSolver; 설치 시 CalculiXSolver).
- FreeCAD 설치 시 기하 유효성은 실제 isValid() 사용.
"""
from __future__ import annotations

from typing import Optional

from ..geometry.bracket import BracketModel
from ..geometry.runner import freecad_available
from ..spec import DesignSpec
from .base import Check, ValidationResult
from .dfm import dfm_checks
from .fatigue import estimate_fatigue
from .structural import AnalyticBendingSolver, StructuralSolver


def run_validation(model: BracketModel, spec: DesignSpec,
                   solver: Optional[StructuralSolver] = None) -> ValidationResult:
    solver = solver or AnalyticBendingSolver()
    res = ValidationResult()

    # (a) 기하 유효성 ---------------------------------------------------
    geom_ok = model.thickness_mm > 0 and model.width_mm > 0 and model.depth_mm > 0
    detail = "치수 양수"
    if freecad_available():
        try:
            shape = model.to_freecad()
            geom_ok = bool(shape.isValid()) and bool(shape.Solids)
            detail = "FreeCAD isValid + 솔리드"
        except Exception as e:
            geom_ok = False
            detail = f"FreeCAD 빌드 실패: {e}"
    res.checks.append(Check("geometry", geom_ok, model.thickness_mm, ">0 / 유효 솔리드", detail))

    # (b) 구조 강도(안전계수) — 솔버 주입 -------------------------------
    sr = solver.solve(model, spec)
    res.metrics["safety_factor"] = sr.safety_factor
    res.metrics["max_stress_MPa"] = sr.max_stress_MPa
    res.checks.append(Check(
        "safety_factor", sr.safety_factor >= spec.targets.safety_factor, sr.safety_factor,
        f">= {spec.targets.safety_factor}",
        f"[{sr.method}] 최대응력 {sr.max_stress_MPa:.1f}MPa, SF {sr.safety_factor:.2f}",
    ))

    # (c) DFM(제조성) ---------------------------------------------------
    for c in dfm_checks(model, spec):
        res.checks.append(c)

    # (d) 피로 내구(선택) ----------------------------------------------
    if spec.targets.min_fatigue_cycles is not None:
        fr = estimate_fatigue(model, spec)
        res.metrics["fatigue_cycles"] = fr.cycles
        res.metrics["stress_amp_MPa"] = fr.stress_amp_MPa
        res.checks.append(Check(
            "fatigue", fr.cycles >= spec.targets.min_fatigue_cycles, fr.cycles,
            f">= {spec.targets.min_fatigue_cycles:.0e} cyc",
            f"σa {fr.stress_amp_MPa:.1f}MPa, 수명 {fr.cycles:.1e}cyc ({fr.note})",
        ))

    # (e) 모달(선택) ----------------------------------------------------
    if spec.targets.min_natural_freq_hz is not None:
        f1 = model.first_natural_freq_hz()
        res.metrics["first_freq_hz"] = f1
        res.checks.append(Check(
            "modal_freq", f1 >= spec.targets.min_natural_freq_hz, f1,
            f">= {spec.targets.min_natural_freq_hz} Hz", f"1차 고유진동수 {f1:.0f}Hz",
        ))

    # (f) 질량 상한(선택, 경량화) ---------------------------------------
    m = model.mass_kg()
    res.metrics["mass_kg"] = m
    if spec.targets.max_mass_kg is not None:
        res.checks.append(Check(
            "mass", m <= spec.targets.max_mass_kg, m,
            f"<= {spec.targets.max_mass_kg} kg", f"질량 {m*1000:.0f}g",
        ))

    return res
