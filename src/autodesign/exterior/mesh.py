"""차량 컨셉 3D 메시 생성 (text→3D concept 목표의 산출물).

무거운 AI 모델(TRELLIS/Hunyuan3D) 없이도 **의존성 0**으로 실제 OBJ 메시를 만드는
절차적(procedural) 차체 생성기를 제공한다. AI 생성기는 설치 시 어댑터로 끼운다
(구조 부품의 FreeCAD 패턴과 동일: 실 도구 있으면 사용, 없으면 절차적 폴백).

※ 여기서 만드는 것은 '설계'가 아니라 '컨셉 셸'이다. 공력/패키징 검토용 형상이며,
  제조용 Class-A 서피스는 별도(상용) 영역(DESIGN.md §8.3).
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from .concept import ConceptSpec

Vec3 = Tuple[float, float, float]


def _interp(u: float, pts: List[Tuple[float, float]]) -> float:
    """제어점 (u, value) 리스트를 선형 보간."""
    if u <= pts[0][0]:
        return pts[0][1]
    if u >= pts[-1][0]:
        return pts[-1][1]
    for (u0, v0), (u1, v1) in zip(pts, pts[1:]):
        if u0 <= u <= u1:
            t = (u - u0) / (u1 - u0) if u1 > u0 else 0.0
            return v0 + (v1 - v0) * t
    return pts[-1][1]


@dataclass
class ConceptMesh:
    """삼각/사각 폴리곤 메시 (컨셉 셸)."""
    vertices: List[Vec3] = field(default_factory=list)
    faces: List[Tuple[int, ...]] = field(default_factory=list)   # 0-based 인덱스
    source: str = "procedural"

    @property
    def n_vertices(self) -> int:
        return len(self.vertices)

    @property
    def n_faces(self) -> int:
        return len(self.faces)

    def bbox_mm(self) -> Tuple[Vec3, Vec3]:
        xs = [v[0] for v in self.vertices]
        ys = [v[1] for v in self.vertices]
        zs = [v[2] for v in self.vertices]
        return (min(xs), min(ys), min(zs)), (max(xs), max(ys), max(zs))

    def write_obj(self, path: str) -> str:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(f"# AutoDesign-LLM concept mesh (source={self.source})\n")
            f.write(f"o {os.path.splitext(os.path.basename(path))[0]}\n")
            for (x, y, z) in self.vertices:
                f.write(f"v {x:.3f} {y:.3f} {z:.3f}\n")
            for face in self.faces:                       # OBJ는 1-based
                f.write("f " + " ".join(str(i + 1) for i in face) + "\n")
        return path


def build_car_mesh(concept: ConceptSpec, n_stations: int = 24) -> ConceptMesh:
    """ConceptSpec 파라미터로 차체 셸을 로프트(loft) 생성.

    길이방향(x)으로 단면(직사각형)을 쌓아 옆모습 실루엣을 만든다.
    - 높이 프로파일: 보닛(낮음)→윈드실드→루프(피크)→리어(유선형 s가 클수록 낮고 긴 패스트백)
    - 폭 프로파일: 노즈/테일에서 좁아지는 평면 테이퍼
    결과는 닫힌(watertight) 사각형 메시.
    """
    L = concept.length_mm
    HW = concept.width_mm / 2.0
    H = concept.height_mm
    s = max(0.0, min(concept.streamline, 1.0))

    # 리어 높이는 유선형이 클수록 낮아짐(패스트백/낮은 트렁크)
    rear = max(0.45, 0.80 - 0.22 * s)
    tail = max(0.20, 0.52 - 0.26 * s)
    height_ctrl = [(0.00, 0.34), (0.12, 0.50), (0.25, 0.72),
                   (0.42, 1.00), (0.60, 0.95), (0.80, rear), (1.00, tail)]
    width_ctrl = [(0.00, 0.52), (0.10, 0.82), (0.25, 0.96), (0.50, 1.00),
                  (0.75, 0.97), (0.90, 0.86), (1.00, 0.60)]

    mesh = ConceptMesh(source="procedural")
    # 각 단면 4점: 0=바닥우, 1=바닥좌, 2=상단좌, 3=상단우 (둘레 순서)
    for i in range(n_stations):
        u = i / (n_stations - 1)
        x = u * L
        hw = HW * _interp(u, width_ctrl)
        h = H * _interp(u, height_ctrl)
        mesh.vertices.extend([
            (x, hw, 0.0), (x, -hw, 0.0), (x, -hw, h), (x, hw, h),
        ])

    def idx(station: int, corner: int) -> int:
        return station * 4 + corner

    # 측면 스킨: 인접 단면을 사각형으로 연결(둘레 4변)
    for i in range(n_stations - 1):
        for k in range(4):
            k2 = (k + 1) % 4
            mesh.faces.append((idx(i, k), idx(i, k2), idx(i + 1, k2), idx(i + 1, k)))
    # 앞/뒤 캡
    mesh.faces.append((idx(0, 3), idx(0, 2), idx(0, 1), idx(0, 0)))            # 노즈(외향)
    last = n_stations - 1
    mesh.faces.append((idx(last, 0), idx(last, 1), idx(last, 2), idx(last, 3)))  # 테일
    return mesh


# --------------------------------------------------------- 생성기 어댑터
class ConceptMeshGenerator:
    """text→3D 메시 생성기 인터페이스."""
    name = "base"

    def available(self) -> bool:
        return False

    def generate_mesh(self, concept: ConceptSpec, prompt: str = "") -> ConceptMesh:
        raise NotImplementedError


class ProceduralCarMesh(ConceptMeshGenerator):
    """의존성 없는 절차적 차체 생성기(항상 사용 가능)."""
    name = "procedural"

    def available(self) -> bool:
        return True

    def generate_mesh(self, concept: ConceptSpec, prompt: str = "") -> ConceptMesh:
        return build_car_mesh(concept)


class _AIMeshGenerator(ConceptMeshGenerator):
    """AI(text→mesh) 어댑터 공통 — 모듈 설치 시 활성. 미설치면 available()=False."""
    module = ""

    def available(self) -> bool:
        import importlib.util
        return importlib.util.find_spec(self.module) is not None

    def generate_mesh(self, concept: ConceptSpec, prompt: str = "") -> ConceptMesh:
        # 실제 연결 자리: prompt→메시 추론 후 ConceptMesh로 정규화.
        # (모델 가중치·GPU 필요) 미구현 시 절차적 폴백을 명시적으로 사용.
        raise RuntimeError(
            f"{self.name} 어댑터는 모델 연결이 필요합니다. 절차적 생성기로 폴백하세요."
        )


class TrellisMesh(_AIMeshGenerator):
    name = "trellis"
    module = "trellis"


class Hunyuan3DMesh(_AIMeshGenerator):
    name = "hunyuan3d"
    module = "hy3dgen"


def get_concept_mesh_generator(prefer: str = "auto") -> ConceptMeshGenerator:
    """메시 생성기 선택. AI 도구가 설치돼 있으면 사용, 없으면 절차적 폴백.

    prefer: 'auto' | 'procedural' | 'trellis' | 'hunyuan3d'
    """
    if prefer == "procedural":
        return ProceduralCarMesh()
    candidates = {"trellis": TrellisMesh, "hunyuan3d": Hunyuan3DMesh}
    if prefer in candidates:
        gen = candidates[prefer]()
        return gen if gen.available() else ProceduralCarMesh()
    if prefer == "auto":
        for cls in (TrellisMesh, Hunyuan3DMesh):
            gen = cls()
            if gen.available():
                return gen
        return ProceduralCarMesh()
    return ProceduralCarMesh()
