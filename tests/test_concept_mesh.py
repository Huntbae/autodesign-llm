"""차량 컨셉 3D 메시 산출 테스트 (text→3D concept 목표 검증)."""
from __future__ import annotations

from autodesign.api import design_exterior
from autodesign.exterior import (ConceptSpec, ProceduralCarMesh, build_car_mesh,
                                 get_concept_mesh_generator)


def test_build_car_mesh_topology():
    m = build_car_mesh(ConceptSpec(name="c"), n_stations=24)
    assert m.n_vertices == 24 * 4
    assert m.n_faces == (24 - 1) * 4 + 2          # 측면 스킨 + 앞/뒤 캡
    assert all(0 <= i < m.n_vertices for f in m.faces for i in f)


def test_write_obj_parses(tmp_path):
    m = build_car_mesh(ConceptSpec(name="car"))
    path = m.write_obj(str(tmp_path / "car.obj"))
    text = (tmp_path / "car.obj").read_text()
    v = sum(1 for ln in text.splitlines() if ln.startswith("v "))
    f = sum(1 for ln in text.splitlines() if ln.startswith("f "))
    assert v == m.n_vertices and f == m.n_faces
    assert path.endswith(".obj")


def test_streamline_lowers_tail():
    """유선형이 클수록 리어가 낮아져야 한다(패스트백)."""
    low = build_car_mesh(ConceptSpec(name="a", streamline=0.2))
    high = build_car_mesh(ConceptSpec(name="b", streamline=0.9))
    assert high.bbox_mm()[1][2] <= low.bbox_mm()[1][2]   # 최대 z(높이)


def test_generator_factory_falls_back_to_procedural():
    gen = get_concept_mesh_generator("auto")          # AI 미설치 → 절차적
    assert isinstance(gen, ProceduralCarMesh)
    assert gen.available()


def test_design_exterior_emits_mesh(tmp_path):
    concept, result = design_exterior("쿠페형 차체, 낮은 보닛, Cd 0.30",
                                      mesh=True, out_dir=str(tmp_path))
    assert result.mesh_source == "procedural"
    obj = result.mesh_paths.get("obj", "")
    assert obj.endswith(".obj")
    assert (tmp_path / "car_body_concept.obj").exists()


def test_design_exterior_mesh_disabled(tmp_path):
    _, result = design_exterior("SUV", mesh=False, out_dir=str(tmp_path))
    assert result.mesh_paths == {}
