"""공력 검증 솔버 — 외형의 정량 검증 축(구조의 FEM에 대응).

- AnalyticDragSolver : 형상지표 기반 항력계수 추정(의존성 없음, 보수적 placeholder)
- OpenFOAMSolver     : OpenFOAM(simpleFoam + k-ω SST) 어댑터 자리(스캐폴드)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from .concept import ConceptSpec

AIR_DENSITY = 1.20   # kg/m³


@dataclass
class AeroResult:
    cd: float                 # 항력계수
    frontal_area_m2: float
    speed_ms: float
    drag_N: float
    method: str
    note: str = ""


@runtime_checkable
class AeroSolver(Protocol):
    def solve(self, concept: ConceptSpec, speed_ms: float = 30.0) -> AeroResult: ...


class AnalyticDragSolver:
    """형상지표 streamline → Cd 추정. Cd ≈ 0.45 - 0.20·streamline (0.25~0.45)."""
    name = "analytic-drag"

    def solve(self, concept: ConceptSpec, speed_ms: float = 30.0) -> AeroResult:
        cd = max(0.20, 0.45 - 0.20 * concept.streamline)
        A = concept.frontal_area_m2()
        drag = 0.5 * AIR_DENSITY * speed_ms ** 2 * cd * A
        return AeroResult(cd=cd, frontal_area_m2=A, speed_ms=speed_ms, drag_N=drag,
                          method=self.name, note="형상지표 기반 추정(교육용). 실제는 CFD 필요.")


class OpenFOAMSolver:
    """OpenFOAM 어댑터 — Phase 6 실연결 자리.

    설치 환경에서 구현: 메시(snappyHexMesh/cfMesh) → simpleFoam(k-ω SST)
    → forceCoeffs 로 Cd 추출. 현재는 가용성 확인 + 해석적 폴백.
    """
    name = "openfoam"

    def __init__(self, fallback: AeroSolver | None = None):
        self.fallback = fallback or AnalyticDragSolver()

    def available(self) -> bool:
        import shutil
        return shutil.which("simpleFoam") is not None

    def solve(self, concept: ConceptSpec, speed_ms: float = 30.0) -> AeroResult:
        if not self.available():
            r = self.fallback.solve(concept, speed_ms)
            r.note = "OpenFOAM 미가용 → 해석적 폴백. " + r.note
            return r
        raise NotImplementedError("OpenFOAM CFD 파이프라인은 Phase 6에서 구현 예정.")
