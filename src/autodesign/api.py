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
    cad_paths: Dict[str, str] = field(default_factory=dict)
    cad_note: str = ""

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
                report: bool = False, cad: bool = True, out_dir: str = ".",
                max_iter: int = 8) -> DesignOutcome:
    """구조 부품 설계 파이프라인 전체 실행 (→ 검증된 CAD 파일 산출)."""
    llm = llm or MockLLM()
    kb = kb or KnowledgeBase.load_default()

    spec = llm.parse_spec(request)
    prereview = build_prereview(spec, kb)
    loop_result = DesignLoop(llm, max_iter=max_iter).run(spec)

    outcome = DesignOutcome(spec=spec, prereview=prereview, loop=loop_result)

    if optimize and loop_result.converged and loop_result.model is not None:
        outcome.optimization = lightweight(spec, loop_result.model)

    # 최종 모델 확정(경량화 결과가 있으면 그 모델을 최종으로 반영)
    if outcome.optimization is not None:
        loop_result.model = outcome.optimization.optimized
    final_model = loop_result.model

    # CAD 파일 산출 (수렴 시, FreeCAD 설치 환경에서 STEP/FCStd 생성)
    if cad and loop_result.converged and final_model is not None:
        from .geometry import freecad_available
        if freecad_available():
            try:
                outcome.cad_paths = final_model.export(out_dir)
            except Exception as e:                      # 형상/저장 실패는 치명적 아님
                outcome.cad_note = f"CAD export 실패: {e}"
        else:
            outcome.cad_note = (
                "FreeCAD 미설치 → CAD 파일 미생성(dry-run). "
                "설치(conda install -c conda-forge freecad) 시 STEP/FCStd 자동 산출."
            )

    if report:
        outcome.report_paths = build_report(loop_result, prereview, out_dir=out_dir)

    return outcome


def design_exterior(request: str, *, speed_ms: float = 30.0,
                    mesh: bool = True, out_dir: str = ".", prefer_mesh: str = "auto",
                    image: Optional[str] = None, llm: Optional[LLMClient] = None):
    """외형(공력) 개념 설계 파이프라인 (→ 차량 컨셉 3D 메시 산출).

    자연어(+선택 참고 이미지) → 개념 형상 → 공력(Cd) 검증·교정 루프
    → 최종 컨셉을 3D 메시(OBJ)로 산출. llm을 주입하면(로컬 Ollama/클라우드)
    LLM이 묘사를 해석해 컨셉 파라미터를 채우고, 없으면 규칙 기반 파서를 쓴다.
    image가 주어지고 AI 어댑터가 설치돼 있으면 이미지→3D 경로를 사용.
    """
    from .exterior import (ExteriorLoop, MockConceptGenerator,
                           get_concept_mesh_generator)
    if llm is not None and hasattr(llm, "parse_concept"):
        concept = llm.parse_concept(request)
    else:
        concept = MockConceptGenerator().generate(request)
    result = ExteriorLoop(speed_ms=speed_ms).run(concept)

    if mesh and result.concept is not None:
        gen = get_concept_mesh_generator(prefer_mesh)
        try:
            cmesh = gen.generate_mesh(result.concept, prompt=request, image=image)
        except Exception:                       # AI 어댑터 실패 → 절차적 폴백
            from .exterior import ProceduralCarMesh
            gen = ProceduralCarMesh()
            cmesh = gen.generate_mesh(result.concept, prompt=request)
        obj_path = cmesh.write_obj(f"{out_dir}/{result.concept.name}.obj")
        result.mesh_paths = {"obj": obj_path}
        result.mesh_source = cmesh.source

    return concept, result
