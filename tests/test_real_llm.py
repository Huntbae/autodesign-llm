"""실 LLM 백엔드 통합 테스트 — 네트워크 없이 transport/가짜 클라이언트 주입.

R1~R5 검증: JSON 유틸·스키마 재시도·Claude/Ollama 백엔드·코드생성 안전성.
"""
import json

import pytest

from autodesign.geometry.codegen import check_script, run_in_sandbox
from autodesign.llm import GenerationResult, MockLLM, get_llm
from autodesign.llm.cloud_backend import CloudLLM
from autodesign.llm.json_utils import extract_json, validate_against
from autodesign.llm.local_backend import LocalLLM
from autodesign.spec import DESIGN_SPEC_SCHEMA


# ---------------- JSON 유틸 ----------------
def test_extract_json_from_fence():
    assert extract_json("```json\n{\"a\": 1}\n```") == {"a": 1}
    assert extract_json("앞말 {\"b\": 2} 뒷말") == {"b": 2}


def test_validate_against_required_and_enum():
    schema = {"type": "object", "required": ["x"],
              "properties": {"x": {"type": "number"},
                             "m": {"type": "string", "enum": ["A", "B"]}}}
    assert validate_against(schema, {"x": 1}) == []
    assert any("필수" in e for e in validate_against(schema, {}))
    assert any("허용값" in e for e in validate_against(schema, {"x": 1, "m": "Z"}))


# ---------------- transport 주입(백엔드 무관 로직) ----------------
_SPEC_JSON = {
    "part_type": "engine_mount_bracket", "material": "AlSi10Mg",
    "loads": [{"name": "v", "direction": [0, 0, -1], "magnitude_N": 5000}],
    "targets": {"safety_factor": 2.0},
}


def test_parse_spec_via_transport():
    def transport(system, user, schema):
        return dict(_SPEC_JSON)
    llm = CloudLLM(transport=transport)   # transport가 _raw_json 대체
    spec = llm.parse_spec("엔진 브래킷 5kN AlSi10Mg")
    assert spec.material == "AlSi10Mg"
    assert spec.total_load_N() == 5000
    assert spec.targets.safety_factor == 2.0


def test_propose_returns_params_and_rationale():
    def transport(system, user, schema):
        return {"thickness_mm": 9.0, "fillet_mm": 3, "rationale": "굽힘 기반 제안"}
    llm = LocalLLM(transport=transport)
    spec = MockLLM().parse_spec("엔진 브래킷 5kN AlSi10Mg 안전계수 2.0")
    gen = llm.propose(spec)
    assert isinstance(gen, GenerationResult)
    assert gen.params["thickness_mm"] == 9.0
    assert "rationale" not in gen.params       # rationale은 분리
    assert "제안" in gen.rationale


def test_schema_retry_then_succeed():
    calls = {"n": 0}

    def flaky(system, user, schema):
        calls["n"] += 1
        if calls["n"] == 1:
            return {"fillet_mm": 3}            # thickness_mm 누락 → 검증 실패
        return {"thickness_mm": 12.0}          # 재시도 성공
    llm = CloudLLM(transport=flaky, max_retries=2)
    spec = MockLLM().parse_spec("브래킷 5kN AlSi10Mg")
    gen = llm.propose(spec)
    assert gen.params["thickness_mm"] == 12.0
    assert calls["n"] == 2


def test_schema_retry_exhausted_raises():
    def bad(system, user, schema):
        return {"nope": 1}
    llm = CloudLLM(transport=bad, max_retries=1)
    spec = MockLLM().parse_spec("브래킷 5kN AlSi10Mg")
    with pytest.raises(ValueError):
        llm.propose(spec)


# ---------------- Claude 백엔드: 가짜 anthropic 클라이언트 ----------------
class _FakeBlock:
    type = "text"
    def __init__(self, text): self.text = text

class _FakeResp:
    def __init__(self, text): self.content = [_FakeBlock(text)]

class _FakeMessages:
    def __init__(self, fn): self._fn = fn
    def create(self, **kw): return self._fn(**kw)

class _FakeAnthropic:
    def __init__(self, fn): self.messages = _FakeMessages(fn)


def test_cloud_backend_with_injected_client():
    seen = {}

    def fn(**kw):
        seen.update(kw)
        return _FakeResp(json.dumps(_SPEC_JSON))
    llm = CloudLLM(client=_FakeAnthropic(fn))
    spec = llm.parse_spec("엔진 브래킷 5kN")
    assert spec.material == "AlSi10Mg"
    # claude-api 사양 준수 확인
    assert seen["model"] == "claude-opus-4-8"
    assert seen["thinking"] == {"type": "adaptive"}
    assert "format" in seen["output_config"]
    assert "temperature" not in seen and "budget_tokens" not in seen


# ---------------- 팩토리 ----------------
def test_factory_selects_backends():
    assert isinstance(get_llm("mock"), MockLLM)
    assert isinstance(get_llm("cloud"), CloudLLM)     # 생성만(네트워크 미사용)
    assert isinstance(get_llm("local"), LocalLLM)
    with pytest.raises(ValueError):
        get_llm("nonsense")


# ---------------- 코드생성 안전성 ----------------
SAFE_SCRIPT = """
import Part
import math
box = Part.makeBox(10, 20, 5)
shape = box
"""

def test_check_script_accepts_safe():
    assert check_script(SAFE_SCRIPT).safe


@pytest.mark.parametrize("bad", [
    "import os\nshape=1",
    "import Part\nos.system('rm -rf /')",
    "eval('1+1')",
    "import Part\nx=open('/etc/passwd')",
    "import Part\ny=().__class__",
])
def test_check_script_rejects_dangerous(bad):
    r = check_script(bad)
    assert not r.safe and r.violations


def test_sandbox_rejects_unsafe_before_exec():
    res = run_in_sandbox("import os\nos.system('echo hi')")
    assert res["status"] == "rejected"


def test_sandbox_safe_without_freecad():
    res = run_in_sandbox(SAFE_SCRIPT)
    # freecadcmd 미설치 환경 → 안전성 통과 후 unavailable
    assert res["status"] in ("freecad_unavailable", "ok")
