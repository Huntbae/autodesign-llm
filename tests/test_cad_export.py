"""CAD 파일 산출 배선 테스트 (text → CAD file 목표 검증).

FreeCAD 미설치 환경: 우아한 dry-run(파일 미생성 + 안내).
FreeCAD 가용(모의): design_part가 최종 모델의 export()를 호출해 경로를 채운다.
"""
from __future__ import annotations

from autodesign import api
from autodesign.api import design_part

REQ = "엔진 마운트 브래킷, 수직 5kN, 재질 AlSi10Mg, 안전계수 2.0, 피로 내구"


def test_cad_dryrun_without_freecad():
    """미설치 환경에선 파일을 만들지 않고 안내만 남긴다(크래시 없음)."""
    out = design_part(REQ, cad=True)
    assert out.converged
    assert out.cad_paths == {}
    assert "FreeCAD 미설치" in out.cad_note


def test_cad_disabled():
    out = design_part(REQ, cad=False)
    assert out.cad_paths == {}
    assert out.cad_note == ""


def test_cad_export_called_when_available(monkeypatch):
    """FreeCAD 가용을 모의하면 최종 모델의 export()가 호출되고 경로가 채워진다."""
    monkeypatch.setattr("autodesign.geometry.freecad_available", lambda: True)
    captured = {}

    def fake_export(self, out_dir="."):
        captured["thickness"] = self.thickness_mm
        captured["out_dir"] = out_dir
        return {"step": f"{out_dir}/engine_mount_bracket.step",
                "fcstd": f"{out_dir}/engine_mount_bracket.FCStd"}

    monkeypatch.setattr(
        "autodesign.geometry.bracket.BracketModel.export", fake_export, raising=True)

    out = design_part(REQ, cad=True, optimize=True, out_dir="/tmp/cadtest")
    assert out.converged
    assert out.cad_paths.get("step", "").endswith(".step")
    assert out.cad_paths.get("fcstd", "").endswith(".FCStd")
    assert captured["out_dir"] == "/tmp/cadtest"
    # 경량화 최종 모델(포켓 반영)이 export 대상이어야 한다
    assert out.optimization is not None
    assert captured["thickness"] == out.optimization.optimized.thickness_mm


def test_cad_export_failure_is_non_fatal(monkeypatch):
    monkeypatch.setattr("autodesign.geometry.freecad_available", lambda: True)

    def boom(self, out_dir="."):
        raise RuntimeError("형상 생성 실패")

    monkeypatch.setattr(
        "autodesign.geometry.bracket.BracketModel.export", boom, raising=True)
    out = design_part(REQ, cad=True)
    assert out.cad_paths == {}
    assert "CAD export 실패" in out.cad_note
