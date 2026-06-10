"""결정적 Mock LLM 백엔드.

LLM/네트워크 없이 코어 파이프라인을 시연·테스트하기 위한 백엔드.
실제 추론 대신 공학적 휴리스틱으로 파라미터를 제안/교정한다.
→ v1 local_backend(vLLM/Ollama), v3 cloud_backend(Claude)로 교체 가능.
"""
from __future__ import annotations

import math
import re
from typing import Optional

from ..spec import DesignSpec, Load, Targets, MATERIALS
from .base import GenerationResult


class MockLLM:
    """LLMClient 계약의 결정적 구현 (테스트/오프라인 데모용)."""

    # ----------------------------------------------------------- ① 파싱
    def parse_spec(self, natural_language: str) -> DesignSpec:
        """아주 단순한 규칙 기반 파서(데모). 실제 LLM이 대체할 자리."""
        text = natural_language
        # 재료 추출
        material = next((m for m in MATERIALS if m.lower() in text.lower()), "AlSi10Mg")
        # 하중 추출: "5kN", "5000N" 등
        loads = []
        for val, unit in re.findall(r"([\d.]+)\s*(kN|N)", text):
            mag = float(val) * (1000.0 if unit.lower() == "kn" else 1.0)
            loads.append(Load("load", (0.0, 0.0, -1.0), mag))
        if not loads:
            loads = [Load("vertical", (0.0, 0.0, -1.0), 5000.0)]
        # 안전계수 추출: "안전계수 2.0", "SF 2"
        m = re.search(r"(?:안전계수|SF)\D*([\d.]+)", text, re.I)
        sf = float(m.group(1)) if m else 2.0
        # 고유진동수
        mf = re.search(r"([\d.]+)\s*Hz", text, re.I)
        freq = float(mf.group(1)) if mf else None
        # 피로: "피로", "내구" 키워드 → 무한수명(1e6) 목표 / 명시 사이클 우선
        fatigue = None
        fc = re.search(r"([\d.]+)\s*(?:e([\d]+))?\s*사이클", text, re.I)
        if fc:
            fatigue = float(fc.group(1)) * (10 ** int(fc.group(2)) if fc.group(2) else 1)
        elif re.search(r"피로|내구", text):
            fatigue = 1.0e6
        return DesignSpec(
            part_type="engine_mount_bracket",
            material=material,
            loads=loads,
            targets=Targets(safety_factor=sf, min_natural_freq_hz=freq,
                            min_fatigue_cycles=fatigue),
            notes=f"parsed from: {natural_language!r}",
        )

    # ----------------------------------------------------------- ④ 제안
    def propose(self, spec: DesignSpec) -> GenerationResult:
        """초기 두께를 다소 얇게 제안 → 검증에서 보강하도록(루프 시연)."""
        # 의도적으로 얇게 시작(목표 SF의 ~40% 수준)해 자기교정 루프를 보여준다.
        t0 = self._thickness_for_sf(spec, target_sf=spec.targets.safety_factor * 0.4)
        return GenerationResult(
            params={"thickness_mm": round(t0, 2)},
            rationale=(
                f"[사전검토] 재료 {spec.material} (항복 {spec.material_obj().yield_strength_MPa}MPa, "
                f"⚠️출처 검증 필요). 대표하중 {spec.total_load_N():.0f}N, 모멘트암 {spec.arm_length_mm}mm. "
                f"코너 응력집중 회피를 위해 라운드(R) 권장. 초기 두께 {t0:.1f}mm 제안."
            ),
        )

    # ----------------------------------------------------------- ⑥ 교정
    def correct(self, spec: DesignSpec, prev_params: dict, feedback: str) -> GenerationResult:
        """검증 피드백을 보고 지배적 제약(강도/피로)을 만족하도록 두께 보강.

        강도·피로 모두 σ∝1/t² 이므로 두께를 키우면 함께 개선된다.
        실패한 제약들의 요구 두께를 각각 역산해 가장 큰 값을 채택(설계 마진 포함).
        """
        from ..validation.fatigue import thickness_for_infinite_life

        t = float(prev_params.get("thickness_mm", 3.0))
        candidates = [t + 0.1]            # 단조 증가 보장
        reasons = []

        if "safety_factor" in feedback:   # 강도 미달
            t_sf = self._thickness_for_sf(spec, spec.targets.safety_factor) * 1.08
            candidates.append(t_sf)
            reasons.append(f"강도(SF≥{spec.targets.safety_factor})→{t_sf:.1f}mm")
        if "fatigue" in feedback:         # 피로 미달
            t_fat = thickness_for_infinite_life(spec)
            candidates.append(t_fat)
            reasons.append(f"피로(무한수명)→{t_fat:.1f}mm")

        t_new = round(max(candidates), 2)
        return GenerationResult(
            params={"thickness_mm": t_new},
            rationale=f"[교정] 미달 제약 {', '.join(reasons) or '재시도'} → 두께 {t:.2f}→{t_new:.2f}mm 보강.",
        )

    # ----------------------------------------------------------- 헬퍼
    @staticmethod
    def _thickness_for_sf(spec: DesignSpec, target_sf: float) -> float:
        """캔틸레버 굽힘 모델로 목표 SF를 만족하는 두께[mm] 역산.

        σ = 6·F·L /(W·t²)  [N, mm → MPa],  SF = σy/σ  ⇒  t = sqrt(6·F·L·SF/(W·σy))
        """
        F = spec.total_load_N()
        L = spec.arm_length_mm
        W = spec.width_mm
        sy = spec.material_obj().yield_strength_MPa
        t = math.sqrt(6.0 * F * L * target_sf / (W * sy))
        return max(t, 1.0)
