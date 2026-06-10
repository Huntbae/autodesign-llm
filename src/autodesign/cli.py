"""데모 CLI — 자연어 한 줄 → 전체 파이프라인 → 리포트.

구조 부품:
  python -m autodesign.cli "엔진 마운트 브래킷, 수직 5kN, AlSi10Mg, 안전계수 2.0, 150Hz, 피로"
  옵션: --optimize (경량화)  --report (HTML/PDF 보고서)
외형(공력):
  python -m autodesign.cli --exterior "쿠페형 차체, 낮은 보닛, Cd 0.30"
"""
from __future__ import annotations

import sys

from .api import design_exterior, design_part
from .geometry.runner import freecad_available
from .llm import ObservedLLM, get_llm

DEFAULT_REQ = ("엔진 마운트 브래킷, 수직 5kN, 재질 AlSi10Mg, 안전계수 2.0, "
               "1차 고유진동수 150Hz, 피로 내구")
DEFAULT_EXT = "쿠페형 유선형 차체, 낮은 보닛, Cd 0.30"


def main(argv=None) -> int:
    argv = list(argv if argv is not None else sys.argv[1:])
    # --backend VALUE 추출
    backend = "auto"
    if "--backend" in argv:
        i = argv.index("--backend")
        if i + 1 < len(argv):
            backend = argv[i + 1]
            del argv[i:i + 2]
    flags = {f for f in argv if f.startswith("--")}
    args = [a for a in argv if not a.startswith("--")]

    # ----- 평가(회귀) 모드 -----
    if "--eval" in flags:
        from .eval import run_eval
        print(f"[평가] backend={backend}\n")
        print(run_eval(get_llm(backend)).summary())
        return 0

    # ----- 외형(공력) 모드 -----
    if "--exterior" in flags:
        req = " ".join(args) if args else DEFAULT_EXT
        print(f"[외형] 요구사항: {req}\n")
        concept, out = design_exterior(req)
        print(f"개념 형상: streamline={concept.streamline:.2f}, "
              f"전면적={concept.frontal_area_m2():.2f}m², 목표 Cd={concept.target_cd}\n")
        print(out.report())
        import shutil
        if shutil.which("simpleFoam") is None:
            print("\n[안내] OpenFOAM 미설치 → 해석적 공력 추정. 실제 CFD는 설치 후.")
        return 0 if out.converged else 1

    # ----- 구조 부품 모드 -----
    req = " ".join(args) if args else DEFAULT_REQ
    print(f"요구사항: {req}  [backend={backend}]\n")
    llm = get_llm(backend)
    if "--trace" in flags:
        llm = ObservedLLM(llm)
    try:
        outcome = design_part(req, llm=llm,
                              optimize="--optimize" in flags, report="--report" in flags)
    except RuntimeError as e:
        print(f"[백엔드 오류] {e}")
        return 2

    print("── 설계명세(DesignSpec) ──")
    print(outcome.spec.to_json()); print()
    print(outcome.prereview); print()
    print(outcome.loop.report())
    if outcome.optimization:
        print(); print(outcome.optimization.report())
    if outcome.report_paths:
        print("\n검토보고서 생성:")
        for kind, p in outcome.report_paths.items():
            print(f"  - {kind.upper()}: {p}")

    if "--trace" in flags and isinstance(llm, ObservedLLM):
        print(f"\n[관측] {llm.recorder.summary()}")
    if not freecad_available():
        print("\n[안내] FreeCAD 미설치 → dry-run(해석적) 모드. 실제 솔리드/FEM은 설치 후.")
    return 0 if outcome.converged else 1


if __name__ == "__main__":
    raise SystemExit(main())
