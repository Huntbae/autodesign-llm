"""구조 강도 솔버 추상화 (Phase 2).

검증 파이프라인이 솔버 구현을 모른 채 동작하도록 인터페이스로 분리.
- AnalyticBendingSolver : 캔틸레버 굽힘 해석적 모델 (현재 기본, 보수적 placeholder)
- CalculiXSolver        : FreeCAD FEM(CalculiX) 어댑터 — Phase 2 실연결 자리(스캐폴드)

dry-run 환경에서는 Analytic, FreeCAD+CalculiX 설치 시 CalculiX로 교체만 하면 된다.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from ..geometry.bracket import BracketModel
from ..spec import DesignSpec


@dataclass
class StructuralResult:
    max_stress_MPa: float
    safety_factor: float
    method: str
    converged: bool = True
    note: str = ""


@runtime_checkable
class StructuralSolver(Protocol):
    def solve(self, model: BracketModel, spec: DesignSpec) -> StructuralResult: ...


class AnalyticBendingSolver:
    """캔틸레버 굽힘 해석적 솔버. 빠르고 의존성 없음. 보수적 근사."""
    name = "analytic-bending"

    def solve(self, model: BracketModel, spec: DesignSpec) -> StructuralResult:
        sigma = model.max_bending_stress_MPa()
        sf = model.safety_factor()
        return StructuralResult(
            max_stress_MPa=sigma, safety_factor=sf, method=self.name,
            note="해석적 굽힘 근사(교육용). 실제 판정은 FEM 필요.",
        )


class CalculiXSolver:
    """FreeCAD FEM(CalculiX) 어댑터 — Phase 2 실연결 자리.

    설치 환경에서 구현: 메시 생성 → 하중/구속 → ccx 실행 → von Mises 추출 → SF.
    현재는 가용성 확인 + 미구현 안내(분명한 TODO).
    """
    name = "calculix"

    def __init__(self, fallback: StructuralSolver | None = None):
        self.fallback = fallback or AnalyticBendingSolver()

    def available(self) -> bool:
        from ..geometry.runner import freecad_available
        if not freecad_available():
            return False
        try:
            import femtools  # type: ignore  # FreeCAD FEM
            return True
        except Exception:
            return False

    def solve(self, model: BracketModel, spec: DesignSpec) -> StructuralResult:
        if not self.available():
            r = self.fallback.solve(model, spec)
            r.note = "CalculiX 미가용 → 해석적 폴백. " + r.note
            return r
        # TODO(Phase 2): FreeCAD FEM 워크벤치로 메시·해석 수행.
        #   ObjectsFem.makeMeshGmsh → 하중/구속 → makeSolverCalculix → ccx 실행
        #   → 결과 von Mises max 추출 → SF = yield / vm_max
        raise NotImplementedError("CalculiX 해석 파이프라인은 Phase 2에서 구현 예정.")
