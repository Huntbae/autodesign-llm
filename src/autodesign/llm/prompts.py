"""프롬프트 자산 (버전관리 대상). 시스템 프롬프트 + 파라미터 스키마.

원칙(docs/02 §7): 프롬프트는 코드처럼 관리. 출력은 스키마로 강제 후 검증.
"""
from __future__ import annotations

from ..spec import DESIGN_SPEC_SCHEMA, DesignSpec

# 생성/교정용 파라미터 스키마
PARAMS_SCHEMA: dict = {
    "type": "object",
    "required": ["thickness_mm"],
    "properties": {
        "thickness_mm": {"type": "number"},
        "fillet_mm": {"type": "number"},
        "bolt_dia_mm": {"type": "number"},
        "n_bolts": {"type": "integer"},
        "pocket_fraction": {"type": "number"},
        "rationale": {"type": "string"},
    },
}

SYS_PARSE = (
    "당신은 자동차 부품 설계 보조 엔진의 요구사항 파서입니다. "
    "사용자의 자연어 요구를 구조화된 설계명세(JSON)로 변환하세요. "
    "하중 방향은 단위벡터로, 크기는 N으로. 명시되지 않은 값은 합리적 기본값을 쓰되 "
    "재료는 반드시 허용 목록 중에서 고릅니다. JSON만 출력하세요."
)

SYS_PROPOSE = (
    "당신은 자동차 구조부품(브래킷) 설계자입니다. 주어진 설계명세와 (있다면) RAG 근거를 "
    "바탕으로 초기 형상 파라미터를 제안하세요. 코너 응력집중을 피하도록 필렛을 권장하고, "
    "굽힘 강도(σ=6FL/Wt²)와 목표 안전계수를 고려해 두께를 정하세요. "
    "물성·표준 수치는 제공된 근거에 기반해 인용하고, 근거 없는 수치는 단정하지 마세요. "
    "params JSON(rationale 포함)만 출력하세요."
)

SYS_CORRECT = (
    "당신은 설계 자기교정기입니다. 검증 게이트의 미달 피드백을 보고 형상 파라미터를 "
    "수정하세요. 강도/피로 미달은 두께 증가로, 과중량은 포켓(살빼기)으로 대응하되 "
    "안전계수·피로한도를 위반하지 않도록 하세요. params JSON(rationale 포함)만 출력."
)

SYS_CONCEPT = (
    "당신은 자동차 익스테리어 디자이너입니다. 사용자의 자연어 묘사(한국어/영어)를 "
    "차량 컨셉 파라미터 JSON으로 변환하세요. body_type(coupe|sedan|suv|hatch|wagon|pickup)과 "
    "roofline(fastback|notchback|suv|wagon)은 필수. 치수는 mm, streamline은 0(둔함)~1(매끈). "
    "묘사에 없는 값은 생략하세요(기본값이 채워짐). JSON만 출력하세요."
)

SYS_CODEGEN = (
    "당신은 FreeCAD Python 생성기입니다. 주어진 설계명세로 솔리드를 만드는 FreeCAD "
    "스크립트를 작성하세요. 엄격한 제약: (1) import 는 FreeCAD, Part, math 만. "
    "(2) os/sys/subprocess/open/eval/exec/__import__/파일삭제 금지. "
    "(3) 최종 형상을 변수 `shape` 에 둘 것. (4) 주석으로 치수 근거를 남길 것. "
    "코드 블록만 출력하세요."
)


def parse_user(nl: str) -> tuple:
    materials = DESIGN_SPEC_SCHEMA["properties"]["material"]["enum"]
    user = (
        f"요구사항: {nl}\n"
        f"허용 재료: {materials}\n"
        "위 요구를 설계명세 JSON으로 변환하세요."
    )
    return SYS_PARSE, user, DESIGN_SPEC_SCHEMA


def propose_user(spec: DesignSpec, rag_context: str = "") -> tuple:
    mat = spec.material_obj()
    user = (
        f"설계명세:\n{spec.to_json()}\n\n"
        f"재료 물성(참고): 항복 {mat.yield_strength_MPa}MPa, 피로한도 {mat.fatigue_limit_MPa}MPa "
        f"(⚠️출처 검증 필요)\n"
        + (f"\nRAG 근거:\n{rag_context}\n" if rag_context else "")
        + "\n초기 형상 파라미터(params JSON)를 제안하세요."
    )
    return SYS_PROPOSE, user, PARAMS_SCHEMA


def correct_user(spec: DesignSpec, prev_params: dict, feedback: str) -> tuple:
    user = (
        f"설계명세 목표: 안전계수≥{spec.targets.safety_factor}"
        + (f", 피로≥{spec.targets.min_fatigue_cycles:.0e}cyc" if spec.targets.min_fatigue_cycles else "")
        + f"\n현재 파라미터: {prev_params}\n검증 피드백(미달): {feedback}\n"
        "수정된 params JSON을 출력하세요."
    )
    return SYS_CORRECT, user, PARAMS_SCHEMA


def concept_user(nl: str) -> tuple:
    from ..exterior.concept import CONCEPT_SCHEMA
    user = (
        f"차량 디자인 묘사: {nl}\n"
        "위 묘사를 컨셉 파라미터 JSON으로 변환하세요. "
        "예: 낮고 매끈하면 streamline↑·height_mm↓, SUV/박시면 roofline='suv'·ride_height_mm↑."
    )
    return SYS_CONCEPT, user, CONCEPT_SCHEMA


def codegen_user(spec: DesignSpec, feedback: str = "") -> tuple:
    user = (
        f"설계명세:\n{spec.to_json()}\n"
        + (f"\n이전 시도 피드백: {feedback}\n" if feedback else "")
        + "\n위 부품의 FreeCAD 솔리드 생성 스크립트를 작성하세요."
    )
    return SYS_CODEGEN, user
