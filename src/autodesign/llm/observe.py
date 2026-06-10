"""R7 — 관측. LLMClient를 감싸 호출별 지연·성공/실패·횟수를 기록.

토큰 사용량은 백엔드가 노출할 때(cloud usage) on_usage 콜백으로 수집.
JSONL 로그 + 집계 요약 제공.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import List, Optional

from ..spec import DesignSpec
from .base import GenerationResult, LLMClient


@dataclass
class CallEvent:
    method: str
    ok: bool
    latency_s: float
    error: str = ""


@dataclass
class UsageRecorder:
    events: List[CallEvent] = field(default_factory=list)
    log_path: Optional[str] = None

    def record(self, ev: CallEvent) -> None:
        self.events.append(ev)
        if self.log_path:
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(ev.__dict__, ensure_ascii=False) + "\n")

    def summary(self) -> dict:
        n = len(self.events)
        ok = sum(1 for e in self.events if e.ok)
        lat = sum(e.latency_s for e in self.events)
        by = {}
        for e in self.events:
            by[e.method] = by.get(e.method, 0) + 1
        return {"calls": n, "ok": ok, "failed": n - ok,
                "total_latency_s": round(lat, 3),
                "avg_latency_s": round(lat / n, 3) if n else 0.0,
                "by_method": by}


class ObservedLLM:
    """LLMClient 데코레이터 — 메트릭 기록 후 위임."""

    def __init__(self, inner: LLMClient, recorder: Optional[UsageRecorder] = None):
        self.inner = inner
        self.recorder = recorder or UsageRecorder()

    def _timed(self, method: str, fn):
        t0 = time.monotonic()
        try:
            result = fn()
            self.recorder.record(CallEvent(method, True, time.monotonic() - t0))
            return result
        except Exception as e:
            self.recorder.record(CallEvent(method, False, time.monotonic() - t0, str(e)[:120]))
            raise

    def parse_spec(self, natural_language: str) -> DesignSpec:
        return self._timed("parse_spec", lambda: self.inner.parse_spec(natural_language))

    def propose(self, spec: DesignSpec, *a, **k) -> GenerationResult:
        return self._timed("propose", lambda: self.inner.propose(spec, *a, **k))

    def correct(self, spec: DesignSpec, prev_params: dict, feedback: str) -> GenerationResult:
        return self._timed("correct", lambda: self.inner.correct(spec, prev_params, feedback))

    def generate_freecad_script(self, spec: DesignSpec, feedback: str = "") -> str:
        return self._timed("codegen", lambda: self.inner.generate_freecad_script(spec, feedback))
