"""차량 컨셉 3D 메시 산출 테스트 (text→3D concept 목표 검증)."""
from __future__ import annotations

from autodesign.api import design_exterior
from autodesign.exterior import (ConceptSpec, ProceduralCarMesh, build_car_mesh,
                                 get_concept_mesh_generator)


def test_build_car_mesh_topology():
    m = build_car_mesh(ConceptSpec(name="c"), n_stations=24)
    assert m.n_vertices > 24 * 4                  # 차체 + 4휠
    assert m.n_faces > 0
    assert all(0 <= i < m.n_vertices for f in m.faces for i in f)


def test_body_type_changes_dimensions():
    from autodesign.exterior import MockConceptGenerator
    gen = MockConceptGenerator()
    suv = gen.generate("도심형 SUV, 높은 차체")
    coupe = gen.generate("낮은 스포츠 쿠페, 패스트백")
    assert suv.body_type == "suv" and coupe.body_type == "coupe"
    assert suv.height_mm > coupe.height_mm        # SUV가 더 높다
    assert suv.roofline == "suv" and coupe.roofline == "fastback"
    # 메시 bbox에도 반영
    assert build_car_mesh(suv).bbox_mm()[1][2] > build_car_mesh(coupe).bbox_mm()[1][2]


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


# ---------------- 로컬 LLM 기반 컨셉 해석 (parse_concept) ----------------

def test_parse_concept_via_local_llm_transport():
    """LocalLLM(Ollama 경로)이 컨셉 JSON을 내면 베이스라인에 덮어써진다."""
    from autodesign.llm.local_backend import LocalLLM

    def transport(system, user, schema):
        assert "디자이너" in system
        return {"body_type": "suv", "roofline": "suv",
                "height_mm": 1800, "streamline": 5.0}   # 5.0 → 1.0으로 클램프

    llm = LocalLLM(transport=transport)
    spec = llm.parse_concept("아무 묘사")
    assert spec.body_type == "suv" and spec.roofline == "suv"
    assert spec.height_mm == 1800
    assert spec.streamline == 1.0                        # 범위 클램프 확인


def test_parse_concept_llm_failure_falls_back():
    """LLM이 계속 잘못된 JSON을 내면 규칙 기반 베이스라인으로 폴백."""
    from autodesign.llm.local_backend import LocalLLM

    llm = LocalLLM(transport=lambda s, u, sc: {"wrong": True}, max_retries=0)
    spec = llm.parse_concept("낮은 스포츠 쿠페")
    assert spec.body_type == "coupe"                     # 규칙 파서 결과


def test_design_exterior_uses_injected_llm(tmp_path):
    """design_exterior(llm=)가 LLM의 parse_concept을 실제로 쓴다."""
    from autodesign.llm import MockLLM
    concept, result = design_exterior("높은 SUV", llm=MockLLM(),
                                      mesh=True, out_dir=str(tmp_path))
    assert concept.body_type == "suv"
    assert result.mesh_paths["obj"].endswith(".obj")
