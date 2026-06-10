"""피로 내구 검증 (Phase 4) — 고주기 피로 S-N 근사 + (단일 하중) 수명 추정.

보수적 가정: 굽힘 최대응력을 완전반전 응력진폭(σa)으로 간주.
S-N 근사: (Su, 1e3) ~ (Se, 1e6) 로그-로그 직선(Basquin 영역).
σa ≤ Se 이면 무한수명(run-out, 1e7로 표기).
※ 교육용 근사 — 실제는 부품별 시험데이터·다축/평균응력 보정 필요(P4 후속).
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from ..geometry.bracket import BracketModel
from ..spec import DesignSpec

RUNOUT = 1.0e7  # 무한수명 표기값


@dataclass
class FatigueResult:
    stress_amp_MPa: float
    cycles: float
    infinite_life: bool
    note: str = ""


def estimate_fatigue(model: BracketModel, spec: DesignSpec) -> FatigueResult:
    mat = spec.material_obj()
    sa = model.max_bending_stress_MPa()
    se = mat.fatigue_limit_MPa
    su = mat.ultimate_strength_MPa
    if sa <= se:
        return FatigueResult(sa, RUNOUT, True, "σa ≤ 피로한도 → 무한수명(run-out)")
    if sa >= su:
        return FatigueResult(sa, 1.0e3, False, "σa ≥ 인장강도 → 저주기/즉시 위험")
    # 로그-로그 보간: logN = 3 + 3·(logSu - logσa)/(logSu - logSe)
    logN = 3.0 + 3.0 * (math.log10(su) - math.log10(sa)) / (math.log10(su) - math.log10(se))
    return FatigueResult(sa, 10.0 ** logN, False, "고주기 S-N 보간 추정")


def thickness_for_infinite_life(spec: DesignSpec, margin: float = 1.05) -> float:
    """σa ≤ Se 를 만족하는 최소 두께[mm] 역산 (캔틸레버 굽힘)."""
    F = spec.total_load_N()
    L = spec.arm_length_mm
    W = spec.width_mm
    se = spec.material_obj().fatigue_limit_MPa
    return math.sqrt(6.0 * F * L / (W * se)) * margin
