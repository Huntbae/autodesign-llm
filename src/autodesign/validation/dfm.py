"""DFM(제조성) 검증 규칙 (Phase 1).

규칙 기반 + 형상 질의. 다이캐스팅/머시닝 공통의 보수적 기준(데모값).
실제 기준은 P3에서 RAG(설계규칙 KB)로 대체·정교화.
"""
from __future__ import annotations

from ..geometry.bracket import BracketModel
from ..spec import DesignSpec
from .base import Check

# 데모 기준(자리표시자) — 실제는 공정·재료별 규칙 KB로 교체
MIN_WALL_MM = 2.0          # 최소 벽두께
MIN_FILLET_MM = 1.5        # 최소 코너 라운드(응력집중 완화)
MIN_HOLE_EDGE_MM = 4.0     # 볼트 홀 중심-모서리 최소 거리


def dfm_checks(model: BracketModel, spec: DesignSpec):
    checks = []
    checks.append(Check(
        "dfm_wall", model.thickness_mm >= MIN_WALL_MM, model.thickness_mm,
        f">= {MIN_WALL_MM} mm", "최소 벽두께",
    ))
    checks.append(Check(
        "dfm_fillet", model.fillet_mm >= MIN_FILLET_MM, model.fillet_mm,
        f">= {MIN_FILLET_MM} mm", "코너 라운드(응력집중 완화)",
    ))
    edge = model.hole_edge_distance_mm()
    checks.append(Check(
        "dfm_hole_edge", edge >= MIN_HOLE_EDGE_MM, edge,
        f">= {MIN_HOLE_EDGE_MM} mm", "볼트 홀 모서리 여유",
    ))
    return checks
