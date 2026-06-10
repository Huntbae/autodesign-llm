"""Phase 1/2 — DFM 체크 + 구조 솔버 추상화 테스트."""
from autodesign.geometry.bracket import build_bracket
from autodesign.spec import DesignSpec, Load, Targets
from autodesign.validation import run_validation, AnalyticBendingSolver, CalculiXSolver


def _spec():
    return DesignSpec(
        part_type="engine_mount_bracket", material="AlSi10Mg",
        loads=[Load("v", (0, 0, -1), 5000)],
        arm_length_mm=20, width_mm=40, depth_mm=40,
        targets=Targets(safety_factor=2.0),
    )


def test_dfm_checks_present():
    spec = _spec()
    model = build_bracket(spec, {"thickness_mm": 12.0})
    res = run_validation(model, spec)
    names = {c.name for c in res.checks}
    assert {"dfm_wall", "dfm_fillet", "dfm_hole_edge"} <= names


def test_thin_part_fails_wall_dfm():
    spec = _spec()
    model = build_bracket(spec, {"thickness_mm": 1.0})  # < 최소 벽두께 2mm
    res = run_validation(model, spec)
    wall = next(c for c in res.checks if c.name == "dfm_wall")
    assert not wall.passed


def test_calculix_falls_back_when_unavailable():
    """CalculiX 미설치 환경: 해석적 폴백으로 동작(예외 없이)."""
    spec = _spec()
    model = build_bracket(spec, {"thickness_mm": 12.0})
    solver = CalculiXSolver()              # fallback=AnalyticBendingSolver
    r = solver.solve(model, spec)
    assert r.safety_factor > 0
    assert "폴백" in r.note or r.method == "calculix"


def test_solver_injection_matches_analytic():
    spec = _spec()
    model = build_bracket(spec, {"thickness_mm": 12.33})
    res = run_validation(model, spec, solver=AnalyticBendingSolver())
    assert res.metrics["safety_factor"] >= 2.0
