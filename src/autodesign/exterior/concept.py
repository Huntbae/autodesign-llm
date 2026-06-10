"""외형 개념 형상 — 파라메트릭 컨셉(공력 평가용 추상)."""
from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class ConceptSpec:
    name: str
    length_mm: float = 4500.0
    width_mm: float = 1850.0
    height_mm: float = 1450.0
    streamline: float = 0.4          # 0(둔함)~1(매끈) — 공력 형상 지표
    target_cd: float = 0.30          # 목표 항력계수

    def frontal_area_m2(self) -> float:
        # 전면투영면적 ≈ 폭×높이×충진율
        return (self.width_mm * 1e-3) * (self.height_mm * 1e-3) * 0.85


class MockConceptGenerator:
    """자연어 → 개념 형상(데모). 실제는 TRELLIS/Hunyuan3D/Blender 어댑터로 교체."""

    def generate(self, natural_language: str) -> ConceptSpec:
        t = natural_language
        streamline = 0.4
        if re.search(r"쿠페|스포츠|유선형|낮은|매끈", t):
            streamline = 0.6
        if re.search(r"SUV|박스|각진|높은", t):
            streamline = 0.3
        m = re.search(r"Cd\s*([\d.]+)", t, re.I)
        target = float(m.group(1)) if m else 0.30
        h = 1700.0 if re.search(r"SUV|높은", t) else 1450.0
        return ConceptSpec(name="car_body_concept", height_mm=h,
                           streamline=streamline, target_cd=target)

    def restyle(self, concept: ConceptSpec, delta_streamline: float) -> ConceptSpec:
        from dataclasses import replace
        return replace(concept, streamline=min(concept.streamline + delta_streamline, 1.0))
