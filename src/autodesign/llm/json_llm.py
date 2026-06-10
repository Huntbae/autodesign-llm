"""실 LLM 백엔드 공통 베이스 — LLMClient 계약을 JSON 구조화 출력으로 구현.

백엔드(클라우드/로컬)는 `_raw_json`(+선택 `_raw_text`)만 구현하면 된다.
스키마 검증 실패 시 오류를 모델에 되먹여 재시도한다.
테스트는 `transport`(또는 `text_transport`)를 주입해 네트워크 없이 검증한다.
"""
from __future__ import annotations

from typing import Callable, Optional

from ..spec import DesignSpec
from . import prompts
from .base import GenerationResult
from .json_utils import extract_json, validate_against


class JsonLLMBase:
    def __init__(self, *, transport: Optional[Callable] = None,
                 text_transport: Optional[Callable] = None, max_retries: int = 2):
        self._transport = transport            # (system, user, schema) -> dict|str
        self._text_transport = text_transport  # (system, user) -> str
        self.max_retries = max_retries

    # ---- 백엔드가 구현 ----
    def _raw_json(self, system: str, user: str, schema: dict) -> dict:
        raise NotImplementedError

    def _raw_text(self, system: str, user: str) -> str:
        raise NotImplementedError

    # ---- 공통: 스키마 강제 + 재시도 ----
    def _complete_json(self, system: str, user: str, schema: dict) -> dict:
        last_err = ""
        for attempt in range(self.max_retries + 1):
            u = user if attempt == 0 else (
                f"{user}\n\n[재시도] 이전 응답 오류: {last_err}\n"
                "스키마를 정확히 지켜 JSON만 출력하세요."
            )
            try:
                raw = (self._transport or self._raw_json)(system, u, schema)
                data = raw if isinstance(raw, dict) else extract_json(raw)
            except ValueError as e:          # 빈 응답/파싱 실패 → 재시도
                last_err = str(e)
                continue
            errs = validate_against(schema, data)
            if not errs:
                return data
            last_err = "; ".join(errs)
        raise ValueError(f"LLM JSON 검증 실패: {last_err}")

    def _complete_text(self, system: str, user: str) -> str:
        return (self._text_transport or self._raw_text)(system, user)

    # ---- LLMClient 계약 ----
    def parse_spec(self, natural_language: str) -> DesignSpec:
        system, user, schema = prompts.parse_user(natural_language)
        data = self._complete_json(system, user, schema)
        data.setdefault("part_type", "engine_mount_bracket")
        return DesignSpec.from_dict(data)

    def propose(self, spec: DesignSpec, rag_context: str = "") -> GenerationResult:
        system, user, schema = prompts.propose_user(spec, rag_context)
        data = self._complete_json(system, user, schema)
        rationale = data.pop("rationale", "")
        return GenerationResult(params=data, rationale=rationale)

    def correct(self, spec: DesignSpec, prev_params: dict, feedback: str) -> GenerationResult:
        system, user, schema = prompts.correct_user(spec, prev_params, feedback)
        data = self._complete_json(system, user, schema)
        rationale = data.pop("rationale", "")
        return GenerationResult(params=data, rationale=rationale)

    def parse_concept(self, natural_language: str):
        """자연어 차량 묘사 → ConceptSpec (LLM 해석 + 규칙 기반 베이스라인).

        규칙 파서로 안전한 베이스라인을 만들고, LLM이 낸 파라미터를 덮어쓴다.
        LLM 실패 시 베이스라인 그대로 반환(파이프라인 중단 없음).
        """
        from ..exterior.concept import MockConceptGenerator, apply_concept_overrides
        base = MockConceptGenerator().generate(natural_language)
        system, user, schema = prompts.concept_user(natural_language)
        try:
            data = self._complete_json(system, user, schema)
        except (ValueError, RuntimeError):     # JSON 불량/백엔드 연결·모델 오류 → 폴백
            return base
        data.pop("rationale", None)
        return apply_concept_overrides(base, data)

    # ---- 코드 생성(방식 B) ----
    def generate_freecad_script(self, spec: DesignSpec, feedback: str = "") -> str:
        system, user = prompts.codegen_user(spec, feedback)
        return self._complete_text(system, user)
