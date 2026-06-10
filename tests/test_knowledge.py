"""Phase 3 — 지식베이스/검색/사전검토 테스트."""
from autodesign.knowledge import KnowledgeBase, build_prereview
from autodesign.spec import DesignSpec, Load, Targets


def test_kb_loads_with_sources():
    kb = KnowledgeBase.load_default()
    assert len(kb.chunks) >= 5
    # 모든 청크는 출처 메타를 가진다(검증 추적)
    assert all(c.source for c in kb.chunks)


def test_search_finds_fillet_rule():
    kb = KnowledgeBase.load_default()
    hits = kb.search("코너 필렛 응력집중 완화", k=3)
    assert hits, "검색 결과 없음"
    texts = " ".join(c.text for c, _ in hits)
    assert "필렛" in texts or "라운드" in texts


def test_search_finds_modal_rule():
    kb = KnowledgeBase.load_default()
    hits = kb.search("고유진동수 공진 NVH", k=3)
    assert hits
    assert any("공진" in c.text or "고유진동수" in c.text for c, _ in hits)


def test_prereview_cites_sources_and_flags_placeholder():
    spec = DesignSpec(
        part_type="engine_mount_bracket", material="AlSi10Mg",
        loads=[Load("v", (0, 0, -1), 5000)],
        targets=Targets(safety_factor=2.0, min_natural_freq_hz=150),
    )
    kb = KnowledgeBase.load_default()
    report = build_prereview(spec, kb)
    assert "출처" in report          # 인용 포함
    assert "⚠️" in report            # 자리표시자 물성 경고
