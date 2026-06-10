"""DesignSpec 단위 테스트."""
from autodesign.spec import DesignSpec, Load, Targets, MATERIALS


def test_roundtrip_json():
    spec = DesignSpec(
        part_type="engine_mount_bracket",
        material="AlSi10Mg",
        loads=[Load("v", (0, 0, -1), 5000)],
        targets=Targets(safety_factor=2.0, min_natural_freq_hz=150),
    )
    d = spec.to_dict()
    spec2 = DesignSpec.from_dict(d)
    assert spec2.material == "AlSi10Mg"
    assert spec2.loads[0].magnitude_N == 5000
    assert spec2.targets.safety_factor == 2.0


def test_validate_catches_errors():
    spec = DesignSpec(part_type="x", material="UNKNOWN", loads=[])
    errs = spec.validate()
    assert any("재료" in e for e in errs)
    assert any("하중" in e for e in errs)


def test_total_load():
    spec = DesignSpec(
        part_type="x", material="AlSi10Mg",
        loads=[Load("v", (0, 0, -1), 3000), Load("h", (1, 0, 0), 4000)],
    )
    # 직교 합성: sqrt(3000² + 4000²) = 5000
    assert abs(spec.total_load_N() - 5000.0) < 1e-6


def test_material_library():
    assert "AlSi10Mg" in MATERIALS
    assert MATERIALS["AlSi10Mg"].yield_strength_MPa == 230
