"""Phase 4 — 피로 검증 + 자기교정 + 보고서 테스트."""
import os

from autodesign.geometry.bracket import build_bracket
from autodesign.llm import MockLLM
from autodesign.orchestrator import DesignLoop
from autodesign.reporting import build_html, build_report
from autodesign.spec import DesignSpec, Load, Targets
from autodesign.validation.fatigue import estimate_fatigue, thickness_for_infinite_life


def _spec(fatigue=1.0e6):
    return DesignSpec(
        part_type="engine_mount_bracket", material="AlSi10Mg",
        loads=[Load("v", (0, 0, -1), 5000)],
        arm_length_mm=20, width_mm=40, depth_mm=40,
        targets=Targets(safety_factor=2.0, min_fatigue_cycles=fatigue),
    )


def test_thin_part_fails_fatigue():
    spec = _spec()
    thin = build_bracket(spec, {"thickness_mm": 8.0})
    fr = estimate_fatigue(thin, spec)
    assert not fr.infinite_life
    assert fr.cycles < 1.0e6


def test_thick_part_infinite_life():
    spec = _spec()
    t = thickness_for_infinite_life(spec)
    thick = build_bracket(spec, {"thickness_mm": t})
    fr = estimate_fatigue(thick, spec)
    assert fr.infinite_life


def test_loop_converges_with_fatigue_target():
    """피로 목표가 강도보다 지배적 → 루프가 피로까지 만족시켜 수렴."""
    spec = _spec(fatigue=1.0e6)
    out = DesignLoop(MockLLM(), max_iter=8).run(spec)
    assert out.converged, out.report()
    fin = out.iterations[-1].result
    fat = next(c for c in fin.checks if c.name == "fatigue")
    assert fat.passed
    # 피로 무한수명 두께가 강도 두께보다 두꺼움을 반영(σa≤Se)
    assert out.model.max_bending_stress_MPa() <= spec.material_obj().fatigue_limit_MPa + 1e-6


def test_report_html_has_sections():
    out = DesignLoop(MockLLM(), max_iter=8).run(_spec())
    h = build_html(out, prereview="테스트 사전검토")
    for kw in ["검토보고서", "설계 요구사항", "자기교정 이력", "안전 고지"]:
        assert kw in h


def test_report_files_written(tmp_path):
    out = DesignLoop(MockLLM(), max_iter=8).run(_spec())
    paths = build_report(out, "사전검토", out_dir=str(tmp_path), basename="r")
    assert os.path.exists(paths["html"])
    # reportlab 설치 환경이면 PDF도 생성
    if "pdf" in paths:
        assert os.path.exists(paths["pdf"]) and os.path.getsize(paths["pdf"]) > 0
