"""① 설계명세(DesignSpec) — 자연어 요구사항을 구조화한 표준 데이터 모델.

모든 모듈(생성·검증·교정)이 이 스키마에 의존한다. (개발 순서 ①)
의존성 없이 dataclass + JSON 직렬화로 구현.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple
import json


@dataclass
class Material:
    """재료 물성. ⚠️ 값은 자리표시자 — 실제는 검증된 데이터시트/규격으로 교체."""
    name: str
    density_kg_m3: float
    youngs_modulus_GPa: float
    yield_strength_MPa: float
    ultimate_strength_MPa: float
    fatigue_limit_MPa: float
    poisson: float = 0.33
    source: str = "PLACEHOLDER — 검증된 출처로 교체 필요"


# 데모용 물성 라이브러리 (P3에서 RAG/검증 데이터로 대체)
MATERIALS: Dict[str, Material] = {
    "AlSi10Mg": Material("AlSi10Mg", 2670, 70, 230, 330, 90),
    "S355":     Material("S355(고장력강)", 7850, 210, 355, 510, 160),
    "AZ91D":    Material("AZ91D(Mg합금)", 1810, 45, 160, 250, 70),
}


@dataclass
class Load:
    """하중: 방향(단위벡터 권장)과 크기[N]."""
    name: str
    direction: Tuple[float, float, float]
    magnitude_N: float


@dataclass
class Targets:
    """검증 목표치."""
    safety_factor: float = 2.0          # 정적 강도 안전계수
    min_natural_freq_hz: Optional[float] = None   # 1차 고유진동수 하한
    min_fatigue_cycles: Optional[float] = None     # 목표 피로 사이클
    max_mass_kg: Optional[float] = None            # 질량 상한(경량화)


@dataclass
class DesignSpec:
    """구조화된 설계 명세 — 시스템의 단일 진실 공급원(SSOT)."""
    part_type: str                      # 예: "engine_mount_bracket"
    material: str                       # MATERIALS 키
    loads: List[Load] = field(default_factory=list)
    mounts: List[Tuple[float, float, float]] = field(default_factory=list)  # 장착점 좌표[mm]
    arm_length_mm: float = 20.0         # 하중점까지 모멘트 암
    width_mm: float = 40.0              # 단면 폭
    depth_mm: float = 40.0              # 깊이
    targets: Targets = field(default_factory=Targets)
    notes: str = ""

    # --- 편의 ---
    def material_obj(self) -> Material:
        if self.material not in MATERIALS:
            raise KeyError(f"미등록 재료: {self.material} (가능: {list(MATERIALS)})")
        return MATERIALS[self.material]

    def total_load_N(self) -> float:
        """대표 하중 크기(벡터 합의 크기)."""
        import math
        sx = sum(l.direction[0] * l.magnitude_N for l in self.loads)
        sy = sum(l.direction[1] * l.magnitude_N for l in self.loads)
        sz = sum(l.direction[2] * l.magnitude_N for l in self.loads)
        return math.sqrt(sx * sx + sy * sy + sz * sz)

    # --- 직렬화 ---
    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self, **kw) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2, **kw)

    @classmethod
    def from_dict(cls, d: dict) -> "DesignSpec":
        d = dict(d)
        d["loads"] = [Load(**l) if isinstance(l, dict) else Load(*l) for l in d.get("loads", [])]
        d["mounts"] = [tuple(m) for m in d.get("mounts", [])]
        t = d.get("targets", {})
        d["targets"] = Targets(**t) if isinstance(t, dict) else t
        # material 객체가 끼어든 경우 정리
        d.pop("__dummy__", None)
        return cls(**d)

    def validate(self) -> List[str]:
        """기본 정합성 검사 — 문제 메시지 리스트(빈 리스트면 통과)."""
        errs: List[str] = []
        if self.material not in MATERIALS:
            errs.append(f"미등록 재료: {self.material}")
        if not self.loads:
            errs.append("하중(loads)이 비어 있음")
        if self.width_mm <= 0 or self.depth_mm <= 0:
            errs.append("단면 치수는 양수여야 함")
        if self.targets.safety_factor <= 0:
            errs.append("안전계수 목표는 양수여야 함")
        return errs


# JSON Schema (LLM 출력 강제용 — llm 백엔드에서 사용)
DESIGN_SPEC_SCHEMA: dict = {
    "type": "object",
    "required": ["part_type", "material", "loads"],
    "properties": {
        "part_type": {"type": "string"},
        "material": {"type": "string", "enum": list(MATERIALS.keys())},
        "arm_length_mm": {"type": "number"},
        "width_mm": {"type": "number"},
        "depth_mm": {"type": "number"},
        "loads": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["name", "direction", "magnitude_N"],
                "properties": {
                    "name": {"type": "string"},
                    "direction": {"type": "array", "items": {"type": "number"},
                                  "minItems": 3, "maxItems": 3},
                    "magnitude_N": {"type": "number"},
                },
            },
        },
        "targets": {
            "type": "object",
            "properties": {
                "safety_factor": {"type": "number"},
                "min_natural_freq_hz": {"type": ["number", "null"]},
                "min_fatigue_cycles": {"type": ["number", "null"]},
                "max_mass_kg": {"type": ["number", "null"]},
            },
        },
    },
}
