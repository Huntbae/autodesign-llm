"""Hermes 백엔드 — 함수호출 포맷 파싱/빌드/통합 테스트 (오프라인)."""
import pytest

from autodesign.llm import GenerationResult, MockLLM, get_llm
from autodesign.llm.hermes import build_tool_system, parse_tool_call
from autodesign.llm.hermes_backend import HermesLLM
from autodesign.llm.json_utils import extract_json


# ---- 파서 ----
def test_parse_tool_call_unwraps_arguments():
    c = '<tool_call>\n{"name": "emit", "arguments": {"thickness_mm": 10.0}}\n</tool_call>'
    assert parse_tool_call(c) == {"thickness_mm": 10.0}


def test_parse_tool_call_plain_json_fallback():
    assert parse_tool_call('{"thickness_mm": 7}') == {"thickness_mm": 7}


def test_parse_tool_call_no_arguments_key():
    c = '<tool_call>{"thickness_mm": 5}</tool_call>'
    assert parse_tool_call(c) == {"thickness_mm": 5}


def test_extract_json_handles_tool_call_tags():
    assert extract_json('<tool_call>{"a": 1}</tool_call>') == {"a": 1}


def test_build_tool_system_includes_schema_and_base():
    schema = {"type": "object", "required": ["thickness_mm"],
              "properties": {"thickness_mm": {"type": "number"}}}
    s = build_tool_system("BASE_SYS", schema, fn="emit_params")
    assert "<tools>" in s and "emit_params" in s and "BASE_SYS" in s
    assert "thickness_mm" in s


# ---- 통합: _chat 대체 ----
class _NativeHermes(HermesLLM):
    """네이티브 tool_call 경로를 흉내내는 가짜 _chat."""
    def _chat(self, system, user, fmt=None):
        return '<tool_call>{"name":"emit","arguments":{"thickness_mm":11.0,"rationale":"ok"}}</tool_call>'


class _FallbackHermes(HermesLLM):
    """네이티브 실패 → format 폴백 경로."""
    def _chat(self, system, user, fmt=None):
        if fmt is None:
            return "사고 과정만 있고 tool_call 없음"   # 네이티브 파싱 실패 유도
        return '{"thickness_mm": 13.0}'                  # format 경로 성공


def test_hermes_native_tool_call_path():
    llm = _NativeHermes()
    spec = MockLLM().parse_spec("브래킷 5kN AlSi10Mg 안전계수 2.0")
    gen = llm.propose(spec)
    assert isinstance(gen, GenerationResult)
    assert gen.params["thickness_mm"] == 11.0
    assert gen.rationale == "ok"


def test_hermes_format_fallback_path():
    llm = _FallbackHermes()
    spec = MockLLM().parse_spec("브래킷 5kN AlSi10Mg 안전계수 2.0")
    gen = llm.propose(spec)
    assert gen.params["thickness_mm"] == 13.0


# ---- 팩토리 ----
def test_factory_ollama_hermes_default_model():
    llm = get_llm("ollama-hermes")
    assert isinstance(llm, HermesLLM)
    assert llm.model == "hermes3"
