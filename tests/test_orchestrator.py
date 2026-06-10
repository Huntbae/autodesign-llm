"""오케스트레이터 루프 — 골든 케이스(자기교정 수렴) 테스트.

LLM 비결정성 대응: 형상 자체가 아니라 '검증 통과 여부 + 핵심 지표'로 판정.
(docs/02-DEV-PROCESS §5.1)
"""
from autodesign.llm import MockLLM
from autodesign.orchestrator import DesignLoop
from autodesign.spec import DesignSpec, Load, Targets


def make_spec(sf=2.0, freq=None):
    return DesignSpec(
        part_type="engine_mount_bracket",
        material="AlSi10Mg",
        loads=[Load("vertical", (0, 0, -1), 5000)],
        arm_length_mm=20.0, width_mm=40.0, depth_mm=40.0,
        targets=Targets(safety_factor=sf, min_natural_freq_hz=freq),
    )


def test_loop_converges_on_safety_factor():
    """얇게 시작 → 자기교정으로 SF 목표 달성."""
    spec = make_spec(sf=2.0)
    out = DesignLoop(MockLLM(), max_iter=6).run(spec)
    assert out.converged, out.report()
    assert out.model.safety_factor() >= 2.0
    # 의도적으로 얇게 시작하므로 1회 이상 교정이 일어나야 함
    assert out.n_iter >= 2


def test_higher_sf_needs_thicker_part():
    """더 높은 SF 목표 → 더 두꺼운(무거운) 결과 (단조성)."""
    low = DesignLoop(MockLLM(), max_iter=8).run(make_spec(sf=2.0))
    high = DesignLoop(MockLLM(), max_iter=8).run(make_spec(sf=4.0))
    assert low.converged and high.converged
    assert high.model.thickness_mm > low.model.thickness_mm
    assert high.model.mass_kg() > low.model.mass_kg()


def test_modal_target_included():
    spec = make_spec(sf=2.0, freq=100.0)
    out = DesignLoop(MockLLM(), max_iter=8).run(spec)
    names = {c.name for c in out.iterations[-1].result.checks}
    assert "modal_freq" in names


def test_final_passes_all_checks():
    out = DesignLoop(MockLLM(), max_iter=8).run(make_spec(sf=2.5))
    assert out.converged
    assert out.iterations[-1].result.passed
