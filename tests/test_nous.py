"""Nous Hermes 백엔드 — 자격증명 해석 + 구조화 출력 (오프라인, 토큰 미전송)."""
import json

import pytest

from autodesign.llm import MockLLM, get_llm
from autodesign.llm.nous_backend import DEFAULT_BASE, DEFAULT_MODEL, NousHermesLLM, _load_creds


# ---- 자격증명 해석 ----
def test_creds_from_auth_file(tmp_path):
    p = tmp_path / "nous_auth.json"
    p.write_text(json.dumps({"access_token": "T123",
                             "inference_base_url": "https://x/v1",
                             "token_type": "Bearer",
                             "expires_at": "2030-01-01T00:00:00+00:00"}))
    base, tok, ttype, exp = _load_creds(None, None, str(p))
    assert base == "https://x/v1" and tok == "T123" and ttype == "Bearer"
    assert exp == "2030-01-01T00:00:00+00:00"


def test_creds_env_override(monkeypatch):
    monkeypatch.setenv("NOUS_API_KEY", "ENVKEY")
    base, tok, _, _ = _load_creds(None, None, "/nonexistent.json")
    assert tok == "ENVKEY" and base == DEFAULT_BASE


def test_creds_missing_is_lenient():
    base, tok, _, _ = _load_creds(None, None, "/nonexistent.json")
    assert tok is None and base == DEFAULT_BASE   # 구성은 실패하지 않음


def test_expired_token_preflight_message():
    """만료 토큰 → 호출 전에 재로그인 안내."""
    llm = NousHermesLLM(token="x", base_url="http://t",
                        expires_at="2020-01-01T00:00:00+00:00")
    spec = MockLLM().parse_spec("브래킷 5kN AlSi10Mg 안전계수 2.0")
    import pytest as _pt
    with _pt.raises(RuntimeError, match="재로그인"):
        llm.propose(spec)


def test_default_model():
    llm = NousHermesLLM(auth_path="/nonexistent.json", post=lambda p: "{}")
    assert llm.model == DEFAULT_MODEL


# ---- 구조화 출력 (post seam 주입) ----
def test_native_tool_call_path():
    def post(payload):
        return '<tool_call>{"name":"emit","arguments":{"thickness_mm":12.0,"rationale":"ok"}}</tool_call>'
    llm = NousHermesLLM(token="x", base_url="http://t", post=post)
    spec = MockLLM().parse_spec("브래킷 5kN AlSi10Mg 안전계수 2.0")
    gen = llm.propose(spec)
    assert gen.params["thickness_mm"] == 12.0 and gen.rationale == "ok"


def test_json_mode_fallback():
    def post(payload):
        if "response_format" in payload:
            return '{"thickness_mm": 9.5}'
        return "tool_call 없음(사고만)"
    llm = NousHermesLLM(token="x", base_url="http://t", post=post)
    spec = MockLLM().parse_spec("브래킷 5kN AlSi10Mg 안전계수 2.0")
    gen = llm.propose(spec)
    assert gen.params["thickness_mm"] == 9.5


def test_openai_compatible_payload_shape():
    seen = {}
    def post(payload):
        seen.update(payload)
        return '<tool_call>{"arguments":{"thickness_mm":10}}</tool_call>'
    llm = NousHermesLLM(token="x", base_url="http://t", post=post, model="Hermes-4-405B")
    llm.propose(MockLLM().parse_spec("브래킷 5kN AlSi10Mg 안전계수 2.0"))
    assert seen["model"] == "Hermes-4-405B"
    assert seen["messages"][0]["role"] == "system"
    assert seen["stream"] is False


def test_empty_response_raises_value_not_attribute():
    """content=null/빈 응답 → AttributeError가 아니라 ValueError(재시도 소진)."""
    def post(payload):
        return ""   # 모델이 빈/None content 반환하는 상황
    llm = NousHermesLLM(token="x", base_url="http://t", post=post, max_retries=1)
    spec = MockLLM().parse_spec("브래킷 5kN AlSi10Mg 안전계수 2.0")
    with pytest.raises(ValueError):
        llm.propose(spec)


def test_no_token_raises_runtime():
    llm = NousHermesLLM(auth_path="/nonexistent.json")  # post 미주입 → 실제 호출 시 토큰 필요
    spec = MockLLM().parse_spec("브래킷 5kN AlSi10Mg 안전계수 2.0")
    with pytest.raises(RuntimeError):
        llm.propose(spec)


# ---- 팩토리 ----
def test_factory_hermes_routes_to_nous():
    assert isinstance(get_llm("hermes", auth_path="/nonexistent.json"), NousHermesLLM)
    assert isinstance(get_llm("nous", auth_path="/nonexistent.json"), NousHermesLLM)
