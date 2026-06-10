"""Phase 5~7 — 경량화·외형·통합 API 테스트."""
from autodesign.api import design_exterior, design_part
from autodesign.exterior import AnalyticDragSolver, ExteriorLoop, MockConceptGenerator, OpenFOAMSolver
from autodesign.llm import MockLLM
from autodesign.optimization import lightweight
from autodesign.orchestrator import DesignLoop
from autodesign.spec import DesignSpec, Load, Targets


def _spec():
    return DesignSpec(
        part_type="engine_mount_bracket", material="AlSi10Mg",
        loads=[Load("v", (0, 0, -1), 5000)],
        arm_length_mm=20, width_mm=40, depth_mm=40,
        targets=Targets(safety_factor=2.0, min_fatigue_cycles=1.0e6),
    )


# ---- Phase 5 경량화 ----
def test_lightweight_reduces_mass_keeping_feasible():
    spec = _spec()
    base = DesignLoop(MockLLM(), max_iter=8).run(spec).model
    opt = lightweight(spec, base)
    assert opt.feasible_count > 0
    assert opt.optimized.mass_kg() <= base.mass_kg()
    assert opt.mass_reduction >= 0.15            # 최소 15% 경량화 목표
    # 경량화 후에도 모든 검증 통과해야 함
    from autodesign.validation import run_validation
    assert run_validation(opt.optimized, spec).passed


# ---- Phase 6 외형 ----
def test_exterior_loop_converges_to_cd_target():
    gen = MockConceptGenerator()
    concept = gen.generate("쿠페형 유선형 차체, Cd 0.32")
    out = ExteriorLoop(gen, AnalyticDragSolver(), max_iter=10).run(concept)
    assert out.converged, out.report()
    assert out.iterations[-1].aero.cd <= concept.target_cd + 1e-9


def test_openfoam_falls_back_when_unavailable():
    concept = MockConceptGenerator().generate("SUV")
    r = OpenFOAMSolver().solve(concept)
    assert r.cd > 0
    assert "폴백" in r.note or r.method == "openfoam"


# ---- Phase 7 통합 API ----
def test_design_part_api_optimize_and_report(tmp_path):
    outcome = design_part(
        "엔진 마운트 브래킷, 수직 5kN, AlSi10Mg, 안전계수 2.0, 피로 내구",
        optimize=True, report=True, out_dir=str(tmp_path),
    )
    assert outcome.converged
    assert outcome.optimization is not None
    assert "html" in outcome.report_paths
    assert "사전 검토" in outcome.prereview or "사전검토" in outcome.summary()


def test_design_exterior_api():
    concept, out = design_exterior("쿠페형 유선형, Cd 0.30")
    assert out.n_iter >= 1
