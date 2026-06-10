"""평가 케이스 — 자연어 요구 + 기대치(파싱·루프). 골든 회귀의 기준."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class EvalCase:
    name: str
    request: str
    material: str                      # 기대 재료
    safety_factor: float               # 기대 목표 SF
    has_fatigue: bool                  # 피로 목표 존재 여부
    min_freq: Optional[float] = None   # 기대 모달 목표(있으면)


EVAL_CASES = [
    EvalCase("bracket_al_sf2_fatigue",
             "엔진 마운트 브래킷, 수직 5kN, 재질 AlSi10Mg, 안전계수 2.0, 1차 고유진동수 150Hz, 피로 내구",
             material="AlSi10Mg", safety_factor=2.0, has_fatigue=True, min_freq=150.0),
    EvalCase("bracket_steel_sf3",
             "브래킷, 수직 8kN, 재질 S355, 안전계수 3.0",
             material="S355", safety_factor=3.0, has_fatigue=False),
    EvalCase("mount_mg_sf2_5",
             "경량 마운트, 4kN, 재질 AZ91D, 안전계수 2.5, 피로 내구",
             material="AZ91D", safety_factor=2.5, has_fatigue=True),
    EvalCase("default_material",
             "엔진 브래킷, 수직 6kN, 안전계수 2.0",
             material="AlSi10Mg", safety_factor=2.0, has_fatigue=False),  # 재료 미지정→기본
]
