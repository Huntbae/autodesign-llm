"""FreeCAD headless 실행 래퍼.

FreeCAD 미설치 환경에서도 코어가 임포트되도록 지연 임포트 + 가용성 플래그 제공.
실제 설치 시(예: conda install -c conda-forge freecad) 자동으로 실제 경로 사용.
"""
from __future__ import annotations

import importlib
from typing import Optional


def freecad_available() -> bool:
    """현재 인터프리터에서 FreeCAD 모듈을 임포트할 수 있는가."""
    try:
        importlib.import_module("FreeCAD")
        return True
    except Exception:
        return False


def get_freecad():
    """FreeCAD 모듈을 반환(미설치 시 RuntimeError)."""
    if not freecad_available():
        raise RuntimeError(
            "FreeCAD 모듈을 찾을 수 없습니다. dry-run 모드만 가능합니다.\n"
            "설치 예: conda install -c conda-forge freecad  (또는 시스템 패키지)."
        )
    return importlib.import_module("FreeCAD")
