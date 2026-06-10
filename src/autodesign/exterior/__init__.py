"""Phase 6 — 외형(Exterior) 툴체인.

구조 부품과 동일한 '생성→검증→교정' 패턴. 단, 검증 축이 FEM이 아니라 공력(CFD).
- concept : AI/절차적 개념 형상 생성 (TRELLIS/Hunyuan3D/Blender 자리; Mock 제공)
- aero    : 공력 검증 (OpenFOAM 자리; 해석적 항력 추정 제공)
- loop    : 개념→공력→교정 루프 (Cd 목표 달성)
※ 개념 메시는 '설계'가 아닌 '컨셉'. 제조용 Class-A 서피스는 별도(상용) 영역.
"""
from .concept import ConceptSpec, MockConceptGenerator
from .aero import AeroResult, AnalyticDragSolver, OpenFOAMSolver
from .loop import ExteriorLoop, ExteriorResult

__all__ = [
    "ConceptSpec", "MockConceptGenerator",
    "AeroResult", "AnalyticDragSolver", "OpenFOAMSolver",
    "ExteriorLoop", "ExteriorResult",
]
