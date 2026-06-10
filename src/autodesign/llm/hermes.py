"""Hermes(Nous Research) 함수호출 규약 — 프롬프트 빌더 + tool_call 파서.

Hermes 3는 ChatML + `<tool_call>{"arguments":..., "name":...}</tool_call>` 포맷에
파인튜닝되어 있다. 이 모델의 '네이티브' 방식으로 구조화 파라미터를 받아낸다.
참고: ollama.com/library/hermes3, NousResearch/Hermes-3-Llama-3.1.
"""
from __future__ import annotations

import json
import re
from typing import Any

from .json_utils import extract_json

# Hermes 함수호출 시스템 프리앰블 (NousResearch 규약)
HERMES_PREAMBLE = (
    "You are a function calling AI model. You are provided with function "
    "signatures within <tools></tools> XML tags. You may call the function to "
    "obtain the requested structured result. Return the call as a JSON object "
    "with 'name' and 'arguments' within <tool_call></tool_call> XML tags:\n"
    "<tool_call>\n{{\"name\": \"{fn}\", \"arguments\": <args-json>}}\n</tool_call>\n"
    "<tools>\n{tools}\n</tools>\n"
)

_TOOL_CALL_RE = re.compile(r"<tool_call>\s*(\{.*?\})\s*</tool_call>", re.S)


def build_tool_system(base_system: str, schema: dict, fn: str = "emit") -> str:
    """기본 시스템 프롬프트에 Hermes 함수호출 지시를 결합."""
    tool = {"type": "function",
            "function": {"name": fn,
                         "description": "Return the structured result.",
                         "parameters": schema}}
    head = HERMES_PREAMBLE.format(fn=fn, tools=json.dumps(tool, ensure_ascii=False))
    return head + "\n" + base_system


def parse_tool_call(content: str) -> dict:
    """Hermes 응답에서 구조화 결과 추출.

    1) <tool_call>{...}</tool_call> 내부 JSON → arguments 반환(있으면)
    2) 없으면 일반 JSON 추출로 폴백
    """
    m = _TOOL_CALL_RE.search(content or "")
    if m:
        obj = json.loads(m.group(1))
        if isinstance(obj, dict) and "arguments" in obj and isinstance(obj["arguments"], dict):
            return obj["arguments"]
        return obj
    return extract_json(content)
