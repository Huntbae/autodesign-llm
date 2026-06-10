"""사전 검토 리포트 생성 — 검색된 근거를 '인용'하며 작성.

할루시네이션 방지 원칙(docs/04-VARIANT-HYBRID §4.1): 수치·기준은 검색된 출처에
근거해 제시하고, 검증 안 된 값은 ⚠️로 표시한다.
"""
from __future__ import annotations

from typing import List

from ..spec import DesignSpec
from .store import KnowledgeBase


def _query_from_spec(spec: DesignSpec) -> str:
    parts = [spec.part_type, spec.material, "브래킷 응력집중 코너 필렛",
             "볼트 체결 모서리", "고유진동수 NVH 공진", "피로 내구"]
    if spec.targets.min_natural_freq_hz:
        parts.append("모달 고유진동수")
    if spec.targets.min_fatigue_cycles:
        parts.append("피로 사이클")
    return " ".join(parts)


def build_prereview(spec: DesignSpec, kb: KnowledgeBase, k: int = 4) -> str:
    """설계명세에 대한 사전 검토 리포트(인용 포함) 문자열."""
    hits = kb.search(_query_from_spec(spec), k=k)
    lines: List[str] = ["── 사전 검토 리포트 (RAG 근거) ──"]

    mat = spec.material_obj()
    lines.append(f"• 재료: {spec.material} (밀도 {mat.density_kg_m3} kg/m³)")
    if "PLACEHOLDER" in mat.source:
        lines.append(f"  ⚠️ 물성 출처 미검증: 항복 {mat.yield_strength_MPa}MPa·피로한도 "
                     f"{mat.fatigue_limit_MPa}MPa는 자리표시자 — 데이터시트로 교체 필요.")
    lines.append(f"• 대표하중 {spec.total_load_N():.0f} N, 모멘트암 {spec.arm_length_mm} mm, "
                 f"목표 SF {spec.targets.safety_factor}"
                 + (f", 1차 고유진동수 ≥ {spec.targets.min_natural_freq_hz}Hz"
                    if spec.targets.min_natural_freq_hz else ""))

    if hits:
        lines.append("• 관련 설계 근거:")
        for i, (c, score) in enumerate(hits, 1):
            lines.append(f"  [{i}] {c.text}")
            lines.append(f"      ↳ 출처: {c.source}  (관련도 {score:.2f})")
    else:
        lines.append("• 관련 근거를 찾지 못함(지식베이스 보강 필요).")

    lines.append("• 결론: 위 근거에 따라 코너 필렛·홀 모서리 여유·모달 분리를 검증 게이트에서 확인.")
    return "\n".join(lines)
