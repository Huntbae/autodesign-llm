"""R6/R7 — 평가 러너 + 관측 래퍼 + 캐싱 테스트 (오프라인)."""
import json

from autodesign.eval import EVAL_CASES, run_eval
from autodesign.eval.runner import _check_parse
from autodesign.llm import MockLLM, ObservedLLM, UsageRecorder
from autodesign.llm.cloud_backend import CloudLLM


# ---- R6 평가 ----
def test_eval_mock_passes_all():
    report = run_eval(MockLLM())
    assert len(report.results) == len(EVAL_CASES)
    assert report.parse_accuracy == 1.0, report.summary()
    assert report.loop_pass_rate == 1.0, report.summary()
    assert report.score == 1.0


def test_eval_parse_only_fast():
    report = run_eval(MockLLM(), run_loop=False)
    assert report.parse_accuracy == 1.0


def test_eval_detects_bad_parse():
    """일부러 틀리게 파싱하는 LLM → 평가가 회귀를 잡아냄."""
    class BadLLM(MockLLM):
        def parse_spec(self, nl):
            spec = super().parse_spec(nl)
            spec.material = "S355"   # 무조건 S355로 오답
            return spec
    report = run_eval(BadLLM(), run_loop=False)
    assert report.parse_accuracy < 1.0


# ---- R7 관측 ----
def test_observed_llm_records_calls():
    rec = UsageRecorder()
    llm = ObservedLLM(MockLLM(), rec)
    spec = llm.parse_spec("브래킷 5kN AlSi10Mg 안전계수 2.0")
    gen = llm.propose(spec)
    llm.correct(spec, gen.params, "[safety_factor] 미달 ; SF=0.8")
    s = rec.summary()
    assert s["calls"] == 3 and s["failed"] == 0
    assert s["by_method"]["parse_spec"] == 1
    assert s["by_method"]["propose"] == 1


def test_observed_llm_records_failure():
    class Boom(MockLLM):
        def parse_spec(self, nl): raise RuntimeError("x")
    rec = UsageRecorder()
    llm = ObservedLLM(Boom(), rec)
    try:
        llm.parse_spec("...")
    except RuntimeError:
        pass
    assert rec.summary()["failed"] == 1


def test_observed_log_jsonl(tmp_path):
    path = str(tmp_path / "trace.jsonl")
    llm = ObservedLLM(MockLLM(), UsageRecorder(log_path=path))
    llm.parse_spec("브래킷 5kN AlSi10Mg")
    lines = open(path, encoding="utf-8").read().strip().splitlines()
    assert len(lines) == 1 and json.loads(lines[0])["method"] == "parse_spec"


# ---- R7 캐싱: cloud 시스템 prefix에 cache_control ----
def test_cloud_system_prompt_is_cached():
    seen = {}

    class _Blk:
        type = "text"
        def __init__(self, t): self.text = t

    class _Resp:
        def __init__(self, t): self.content = [_Blk(t)]

    class _Msgs:
        def create(self, **kw):
            seen.update(kw)
            return _Resp('{"thickness_mm": 10}')

    class _Client:
        messages = _Msgs()

    llm = CloudLLM(client=_Client())
    spec = MockLLM().parse_spec("브래킷 5kN AlSi10Mg 안전계수 2.0")
    llm.propose(spec)
    assert isinstance(seen["system"], list)
    assert seen["system"][0]["cache_control"] == {"type": "ephemeral"}
