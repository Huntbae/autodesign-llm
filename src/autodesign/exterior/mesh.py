"""차량 컨셉 3D 메시 생성 (text→3D concept 목표의 산출물).

무거운 AI 모델(TRELLIS/Hunyuan3D) 없이도 **의존성 0**으로 실제 OBJ 메시를 만드는
절차적(procedural) 차체 생성기를 제공한다. 차종·루프라인·비례·휠을 ConceptSpec에서
읽어 옆모습 실루엣과 4개 휠을 가진, '차처럼 보이는' 셸을 만든다.

AI 생성기는 설치 시 어댑터로 끼운다(구조 부품의 FreeCAD 패턴과 동일):
- 텍스트→3D: TRELLIS/Hunyuan3D
- 이미지→3D: Hunyuan3D (참고 사진 1장으로 스타일 근접 — '이 디자인처럼'에 가장 가까운 경로)
※ 절차적/AI 모두 '컨셉 셸'이지 양산 설계가 아니다(DESIGN.md §8.3).
"""
from __future__ import annotations

import math
import os
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from .concept import ConceptSpec

Vec3 = Tuple[float, float, float]


def _interp(u: float, pts: List[Tuple[float, float]]) -> float:
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
    vertices: List[Vec3] = field(default_factory=list)
    faces: List[Tuple[int, ...]] = field(default_factory=list)   # 0-based
    source: str = "procedural"

    @property
    def n_vertices(self) -> int:
        return len(self.vertices)

    @property
    def n_faces(self) -> int:
        return len(self.faces)

    def bbox_mm(self) -> Tuple[Vec3, Vec3]:
        xs = [v[0] for v in self.vertices]; ys = [v[1] for v in self.vertices]
        zs = [v[2] for v in self.vertices]
        return (min(xs), min(ys), min(zs)), (max(xs), max(ys), max(zs))

    def add(self, verts: List[Vec3], faces: List[Tuple[int, ...]]) -> None:
        """다른 파트를 인덱스 오프셋 적용해 병합."""
        off = len(self.vertices)
        self.vertices.extend(verts)
        self.faces.extend(tuple(i + off for i in f) for f in faces)

    def write_obj(self, path: str) -> str:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(f"# AutoDesign-LLM concept mesh (source={self.source})\n")
            f.write(f"o {os.path.splitext(os.path.basename(path))[0]}\n")
            for (x, y, z) in self.vertices:
                f.write(f"v {x:.2f} {y:.2f} {z:.2f}\n")
            for face in self.faces:
                f.write("f " + " ".join(str(i + 1) for i in face) + "\n")
        return path


# ----------------------------------------------------------- 루프라인 프로파일
def _height_profile(spec: ConceptSpec) -> List[Tuple[float, float]]:
    """루프라인별 높이 프로파일(전장 위치 u → 차체 상단 높이 비율 0~1)."""
    s = max(0.0, min(spec.streamline, 1.0))
    hood = spec.hood_frac
    cab_end = min(hood + spec.cab_frac, 0.92)
    if spec.roofline == "notchback":         # 세단: 루프 후 트렁크 단차
        return [(0.0, 0.30), (hood * 0.5, 0.42), (hood, 0.66),
                (hood + 0.06, 0.96), (cab_end, 0.97),
                (cab_end + 0.04, 0.70), (1.0, 0.62)]
    if spec.roofline == "suv":               # SUV/픽업: 높고 평평한 박시 루프
        return [(0.0, 0.42), (hood * 0.6, 0.62), (hood, 0.90),
                (hood + 0.05, 1.0), (0.88, 1.0), (1.0, 0.88)]
    if spec.roofline == "wagon":             # 왜건: 루프가 뒤까지 연장
        return [(0.0, 0.32), (hood, 0.70), (hood + 0.05, 0.98),
                (0.92, 0.96), (1.0, 0.82)]
    # fastback(기본): 매끈한 패스트백, 유선형↑이면 더 낮고 긴 테일
    rear = max(0.42, 0.78 - 0.24 * s)
    tail = max(0.20, 0.52 - 0.26 * s)
    peak = hood + 0.04
    return [(0.0, 0.30), (hood * 0.5, 0.46), (hood, 0.74),
            (peak, 1.0), (min(peak + 0.20, 0.82), rear), (1.0, tail)]


def _width_profile() -> List[Tuple[float, float]]:
    return [(0.00, 0.52), (0.10, 0.82), (0.25, 0.96), (0.50, 1.00),
            (0.75, 0.97), (0.90, 0.84), (1.00, 0.58)]


def _wheel(center: Vec3, r: float, half_w: float, seg: int = 14):
    """Y축(차폭 방향) 원기둥 휠. (verts, faces) 반환."""
    cx, cy, cz = center
    verts: List[Vec3] = []
    for side in (-1, 1):
        y = cy + side * half_w
        for k in range(seg):
            a = 2 * math.pi * k / seg
            verts.append((cx + r * math.cos(a), y, max(cz + r * math.sin(a), 0.0)))
    cl = len(verts); verts.append((cx, cy - half_w, cz)); cr = len(verts); verts.append((cx, cy + half_w, cz))
    faces: List[Tuple[int, ...]] = []
    for k in range(seg):
        k2 = (k + 1) % seg
        faces.append((k, k2, seg + k2, seg + k))          # 트레드(측면)
        faces.append((cl, k2, k))                         # 좌측 캡
        faces.append((cr, seg + k, seg + k2))             # 우측 캡
    return verts, faces


def build_car_mesh(spec: ConceptSpec, n_stations: int = 26) -> ConceptMesh:
    """ConceptSpec(차종·루프라인·비례·휠)으로 차체 셸 + 4휠 메시를 생성."""
    L, HW, H = spec.length_mm, spec.width_mm / 2.0, spec.height_mm
    floor = max(60.0, spec.ride_height_mm)
    body_h = max(H - floor, 600.0)
    hprof, wprof = _height_profile(spec), _width_profile()

    mesh = ConceptMesh(source="procedural")
    body_v: List[Vec3] = []
    for i in range(n_stations):
        u = i / (n_stations - 1)
        x = u * L
        hw = HW * _interp(u, wprof)
        top = floor + body_h * _interp(u, hprof)
        body_v.extend([(x, hw, floor), (x, -hw, floor), (x, -hw, top), (x, hw, top)])

    def idx(st, c): return st * 4 + c
    body_f: List[Tuple[int, ...]] = []
    for i in range(n_stations - 1):
        for k in range(4):
            k2 = (k + 1) % 4
            body_f.append((idx(i, k), idx(i, k2), idx(i + 1, k2), idx(i + 1, k)))
    body_f.append((idx(0, 3), idx(0, 2), idx(0, 1), idx(0, 0)))
    last = n_stations - 1
    body_f.append((idx(last, 0), idx(last, 1), idx(last, 2), idx(last, 3)))
    mesh.add(body_v, body_f)

    # 4휠: 오버행이 짧을수록 축이 양 끝으로 이동(롱휠베이스)
    r = spec.wheel_dia_mm / 2.0
    ww = HW * 0.12
    front_x = L * (0.10 + 0.06 * spec.overhang)
    rear_x = L * (0.90 - 0.06 * spec.overhang)
    track = HW * 0.98
    for ax in (front_x, rear_x):
        for sy in (-track, track):
            wv, wf = _wheel((ax, sy, r), r, ww)
            mesh.add(wv, wf)
    return mesh


# --------------------------------------------------------- 생성기 어댑터
class ConceptMeshGenerator:
    name = "base"

    def available(self) -> bool:
        return False

    def generate_mesh(self, concept: ConceptSpec, prompt: str = "",
                      image: Optional[str] = None) -> ConceptMesh:
        raise NotImplementedError


class ProceduralCarMesh(ConceptMeshGenerator):
    """의존성 없는 절차적 차체 생성기(항상 사용 가능)."""
    name = "procedural"

    def available(self) -> bool:
        return True

    def generate_mesh(self, concept: ConceptSpec, prompt: str = "",
                      image: Optional[str] = None) -> ConceptMesh:
        return build_car_mesh(concept)


class _AIMeshGenerator(ConceptMeshGenerator):
    """AI(text/image→mesh) 어댑터 공통 — 모듈 설치 시 활성."""
    module = ""

    def available(self) -> bool:
        import importlib.util
        return importlib.util.find_spec(self.module) is not None

    def generate_mesh(self, concept: ConceptSpec, prompt: str = "",
                      image: Optional[str] = None) -> ConceptMesh:
        # 실제 연결 자리: image가 있으면 이미지→3D(참고 사진 기반), 없으면 텍스트→3D.
        # 모델 가중치·GPU 필요. 미구현 시 절차적 폴백을 명시적으로 사용.
        raise RuntimeError(
            f"{self.name} 어댑터는 모델 연결(GPU)이 필요합니다. 절차적 생성기로 폴백하세요."
        )


class TrellisMesh(_AIMeshGenerator):
    name = "trellis"; module = "trellis"


class Hunyuan3DMesh(_AIMeshGenerator):
    name = "hunyuan3d"; module = "hy3dgen"


def get_concept_mesh_generator(prefer: str = "auto") -> ConceptMeshGenerator:
    """메시 생성기 선택. AI 도구 설치 시 사용, 없으면 절차적 폴백.

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
