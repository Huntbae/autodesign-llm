"""검증 결과 자료구조 + 체크 계약."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class Check:
    """개별 검증 항목 결과."""
    name: str
    passed: bool
    value: float
    target: str
    detail: str = ""


@dataclass
class ValidationResult:
    """검증 파이프라인 종합 결과."""
    checks: List[Check] = field(default_factory=list)
    metrics: Dict[str, float] = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        return all(c.passed for c in self.checks) and len(self.checks) > 0

    @property
    def failures(self) -> List[Check]:
        return [c for c in self.checks if not c.passed]

    def feedback(self) -> str:
        """LLM 자기교정용 피드백 문자열(미달 항목 + 핵심 지표)."""
        if self.passed:
            return "모든 검증 통과."
        parts = []
        for c in self.failures:
            parts.append(f"[{c.name}] {c.detail} (목표 {c.target})")
        # 구조 미달 시 SF 수치를 명시(MockLLM.correct가 파싱)
        if "safety_factor" in self.metrics:
            parts.append(f"SF={self.metrics['safety_factor']:.2f}")
        return " ; ".join(parts)

    def summary(self) -> str:
        lines = []
        for c in self.checks:
            mark = "✅" if c.passed else "❌"
            lines.append(f"  {mark} {c.name:16s} {c.value:>10.3g}  (목표 {c.target})")
        return "\n".join(lines)
