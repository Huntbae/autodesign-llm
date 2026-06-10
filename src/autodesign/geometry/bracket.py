"""엔진 마운트 브래킷 — 파라메트릭 빌더 + 해석적(dry-run) 모델.

골든 부품(docs/01-ROADMAP 벤치마크 1순위). 단순 L-플레이트 캔틸레버로 모델링.
- dry-run: 부피/질량/굽힘응력/고유진동수를 해석적으로 계산 (FEM 전 시연·테스트용)
- FreeCAD 설치 시: 실제 솔리드 생성(볼트 홀·필렛 포함), STEP/FCStd export
Phase 1: 볼트 홀 + 필렛 + DFM 기하 파라미터 추가.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List, Optional, Tuple

from ..spec import DesignSpec
from .runner import get_freecad


@dataclass
class BracketModel:
    """생성된 브래킷의 파라미터 + 파생 물성."""
    spec: DesignSpec
    thickness_mm: float
    fillet_mm: float = 3.0
    bolt_dia_mm: float = 8.0
    n_bolts: int = 3
    pocket_fraction: float = 0.0   # 저응력부 살빼기(경량화). 0~0.45.

    # --- 치수 ---
    @property
    def width_mm(self) -> float:
        return self.spec.width_mm

    @property
    def depth_mm(self) -> float:
        return self.spec.depth_mm

    @property
    def arm_mm(self) -> float:
        return self.spec.arm_length_mm

    def bolt_positions(self) -> List[Tuple[float, float, float]]:
        """장착점이 명시되면 사용, 없으면 수직 플레이트에 균등 배치(데모)."""
        if self.spec.mounts:
            return list(self.spec.mounts)
        # depth 방향으로 n개 균등 배치, 높이 중앙
        pts = []
        n = max(self.n_bolts, 1)
        for i in range(n):
            y = self.depth_mm * (i + 1) / (n + 1)
            pts.append((self.thickness_mm / 2.0, y, self.width_mm / 2.0))
        return pts

    # --- 파생 물성(해석적) ---
    def volume_mm3(self) -> float:
        """L형 근사(수평+수직 플레이트) - 볼트 홀 - 경량화 포켓."""
        t = self.thickness_mm
        horiz = self.arm_mm * self.depth_mm * t
        vert = self.width_mm * self.depth_mm * t
        holes = self.n_bolts * math.pi * (self.bolt_dia_mm / 2.0) ** 2 * t
        solid = max(horiz + vert - holes, 0.0)
        return solid * (1.0 - self.pocket_fraction)   # 포켓으로 질량 감소

    def effective_width_mm(self) -> float:
        """포켓팅 시 굽힘 유효폭 감소(저응력부 제거의 보수적 페널티)."""
        return self.width_mm * (1.0 - 0.3 * self.pocket_fraction)

    def mass_kg(self) -> float:
        rho = self.spec.material_obj().density_kg_m3
        return self.volume_mm3() * 1e-9 * rho  # mm³→m³

    def max_bending_stress_MPa(self) -> float:
        """캔틸레버 굽힘 최대 응력. σ = 6·F·L/(W·t²)  [N,mm → MPa]."""
        F = self.spec.total_load_N()
        L = self.arm_mm
        W = self.effective_width_mm()
        t = self.thickness_mm
        if t <= 0 or W <= 0:
            return float("inf")
        return 6.0 * F * L / (W * t * t)

    def safety_factor(self) -> float:
        sy = self.spec.material_obj().yield_strength_MPa
        sigma = self.max_bending_stress_MPa()
        return sy / sigma if sigma > 0 else float("inf")

    def first_natural_freq_hz(self) -> float:
        """캔틸레버 1차 고유진동수 근사 (교육용; 실제는 P4 FEM 모달)."""
        E = self.spec.material_obj().youngs_modulus_GPa * 1e9
        W = self.width_mm * 1e-3
        t = self.thickness_mm * 1e-3
        L = max(self.arm_mm * 1e-3, 1e-4)
        I = W * t ** 3 / 12.0
        k = 3.0 * E * I / (L ** 3)
        m_eff = max(0.23 * self.mass_kg(), 1e-6)
        return (1.0 / (2.0 * math.pi)) * math.sqrt(k / m_eff)

    # --- DFM 기하 지표 (Phase 1) ---
    def hole_edge_distance_mm(self) -> float:
        """볼트 홀 중심에서 가장 가까운 자유 모서리까지 거리(근사).

        수직 플레이트에서 깊이방향 균등배치 → 인접 간격/2 와 단부 여유 중 작은 값.
        """
        n = max(self.n_bolts, 1)
        spacing = self.depth_mm / (n + 1)
        return spacing - self.bolt_dia_mm / 2.0

    # --- 실제 형상(FreeCAD) ---
    def to_freecad(self, out_path: Optional[str] = None):
        """FreeCAD 솔리드 생성(볼트 홀·필렛 포함). 미설치 시 RuntimeError."""
        get_freecad()
        import Part  # type: ignore
        from FreeCAD import Vector  # type: ignore

        t, W, D, L = self.thickness_mm, self.width_mm, self.depth_mm, self.arm_mm
        horiz = Part.makeBox(L, D, t)
        vert = Part.makeBox(t, D, W)
        shape = horiz.fuse(vert)

        # 볼트 홀 (수직 플레이트 관통)
        r = self.bolt_dia_mm / 2.0
        for (x, y, z) in self.bolt_positions():
            cyl = Part.makeCylinder(r, t * 1.2, Vector(-0.1, y, z), Vector(1, 0, 0))
            try:
                shape = shape.cut(cyl)
            except Exception:
                pass

        # 필렛 (코너 응력집중 완화)
        if self.fillet_mm > 0:
            try:
                shape = shape.makeFillet(min(self.fillet_mm, t * 0.4), shape.Edges[:4])
            except Exception:
                pass  # 실패 시 무필렛 진행(DFM 검증에서 플래그)

        if out_path:
            if out_path.lower().endswith(".step") or out_path.lower().endswith(".stp"):
                shape.exportStep(out_path)
            else:
                shape.exportBrep(out_path)
        return shape


def build_bracket(spec: DesignSpec, params: dict) -> BracketModel:
    """LLM이 제안한 파라미터로 브래킷 모델 생성."""
    return BracketModel(
        spec=spec,
        thickness_mm=float(params.get("thickness_mm", 3.0)),
        fillet_mm=float(params.get("fillet_mm", 3.0)),
        bolt_dia_mm=float(params.get("bolt_dia_mm", 8.0)),
        n_bolts=int(params.get("n_bolts", spec_n_bolts(spec))),
        pocket_fraction=float(params.get("pocket_fraction", 0.0)),
    )


def spec_n_bolts(spec: DesignSpec) -> int:
    return len(spec.mounts) if spec.mounts else 3
