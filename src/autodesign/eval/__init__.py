"""R6 — 평가셋·회귀 프레임워크. 프롬프트·모델 변경 시 회귀 탐지."""
from .cases import EVAL_CASES, EvalCase
from .runner import EvalReport, run_eval

__all__ = ["EVAL_CASES", "EvalCase", "EvalReport", "run_eval"]
