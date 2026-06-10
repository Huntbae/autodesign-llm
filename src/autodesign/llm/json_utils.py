"""LLM JSON 출력 유틸 — 추출 + 경량 스키마 검증 (의존성 없음)."""
from __future__ import annotations

import json
import re
from typing import Any, List


def extract_json(text: str) -> dict:
    """모델 응답 텍스트에서 첫 JSON 객체를 추출."""
    if isinstance(text, dict):
        return text
    if not text or not str(text).strip():
        raise ValueError("빈 LLM 응답")
    text = str(text).strip()
    # Hermes <tool_call>{...}</tool_call> 언랩
    mt = re.search(r"<tool_call>\s*(\{.*?\})\s*</tool_call>", text, re.S)
    if mt:
        text = mt.group(1)
    # ```json ... ``` 펜스 제거
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.S)
    if m:
        text = m.group(1)
    # 첫 '{' ~ 마지막 '}'
    s, e = text.find("{"), text.rfind("}")
    if s != -1 and e != -1 and e > s:
        text = text[s:e + 1]
    return json.loads(text)


def validate_against(schema: dict, data: Any) -> List[str]:
    """경량 JSON Schema 검증 — required·type·enum만 점검. 오류 메시지 리스트."""
    errs: List[str] = []

    def check(node: dict, value: Any, path: str) -> None:
        t = node.get("type")
        if t == "object":
            if not isinstance(value, dict):
                errs.append(f"{path}: object 기대"); return
            for req in node.get("required", []):
                if req not in value:
                    errs.append(f"{path}.{req}: 필수 누락")
            for k, sub in node.get("properties", {}).items():
                if k in value:
                    check(sub, value[k], f"{path}.{k}")
        elif t == "array":
            if not isinstance(value, list):
                errs.append(f"{path}: array 기대"); return
            items = node.get("items")
            if items:
                for i, v in enumerate(value):
                    check(items, v, f"{path}[{i}]")
        elif t in ("number", "integer"):
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                errs.append(f"{path}: number 기대")
        elif t == "string":
            if not isinstance(value, str):
                errs.append(f"{path}: string 기대")
        if "enum" in node and value not in node["enum"]:
            errs.append(f"{path}: {value!r} 은 허용값 {node['enum']} 아님")

    check(schema, data, "$")
    return errs
