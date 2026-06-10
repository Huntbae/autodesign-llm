# 02. 개발 프로세스 (개발자 관점)

> "어떻게 짜고, 어떤 순서로, 어떻게 검증·배포하는가." 엔지니어링 규율 정의.

- 버전: v0.1 / 작성일: 2026-06-09

---

## 1. 저장소 & 모듈 구조

```
autodesign-llm/
├── core/                  # 버전 공통 코어 (세 변형이 공유)
│   ├── orchestrator/      #   요구사항 파싱·루프 제어
│   ├── geometry/          #   FreeCAD 형상 생성
│   ├── validation/        #   FEM/DFM/기하 검증
│   ├── optimization/      #   위상최적화
│   └── reporting/         #   검토보고서
├── llm/                   # LLM 백엔드 추상화 (★이식성 핵심)
│   ├── base.py            #   LLMClient 인터페이스
│   ├── local_backend.py   #   Ollama/vLLM (v1, v2)
│   └── cloud_backend.py   #   Claude API (v3)
├── knowledge/             # RAG (v2/v3)
│   ├── retriever.py
│   └── ingest.py
├── exterior/              # 외형 툴체인 (P6): Blender/OpenFOAM/NURBS
├── deploy/                # 버전별 배포 설정
│   ├── local/ hybrid/ cloud/
├── tests/                 # 단위·통합·골든 케이스
└── docs/
```

> **설계 원칙**: 변형(v1/v2/v3)은 `llm/`·`knowledge/`·`deploy/`만 갈아끼우고
> `core/`는 공유. 백엔드는 모두 인터페이스(`base.py`) 뒤에 숨긴다.

---

## 2. 인터페이스 우선 설계 (계약)

```python
# llm/base.py
class LLMClient(Protocol):
    def complete(self, prompt: str, *, schema: dict | None = None) -> str | dict: ...

# knowledge/retriever.py
class Retriever(Protocol):
    def search(self, query: str, k: int = 5) -> list[Chunk]: ...

# validation/base.py
class Validator(Protocol):
    def run(self, model: FCModel, spec: DesignSpec) -> ValidationResult: ...
```
세 변형은 동일 계약을 구현 → 코어 코드는 어떤 백엔드인지 모른 채 동작.

---

## 3. 개발 순서 (의존성 기반)

```
① LLM 추상화 + 설계명세 스키마(DesignSpec)   ← 가장 먼저, 모두가 의존
② FreeCAD 실행 래퍼 + 골든 부품 스크립트
③ 기하 검증 (가장 단순한 검증부터)
④ 오케스트레이터 루프 (생성→검증→교정)
⑤ FEM 정적강도 검증
⑥ RAG + 사전검토 (v2 진입)
⑦ 모달·피로·DFM
⑧ 위상최적화
⑨ 외형 툴체인
⑩ UI/패키징
```
원칙: **검증을 먼저, 생성을 나중에**. 검증이 없으면 생성 품질을 측정 불가.

---

## 4. 브랜치 & 협업

- **트렁크 기반 + 단기 피처 브랜치** (`feat/`, `fix/`, `exp/`).
- main은 항상 배포 가능 상태(green CI). PR 필수, 리뷰어 1+.
- 엔지니어링 정합성이 걸린 PR(검증 기준 변경)은 **CAE 엔지니어 승인 필수**.
- 커밋: Conventional Commits (`feat:`, `fix:`, `test:`, `docs:`).

---

## 5. 테스트 전략 (3계층 + 골든)

| 계층 | 대상 | 도구 | 게이트 |
|------|------|------|--------|
| 단위 | 파서·스키마·유틸 | pytest | PR마다 |
| 통합 | FreeCAD/CalculiX 연동 | pytest + headless | PR마다(가능 범위) |
| **골든 케이스** | 벤치마크 부품 회귀 | 저장된 기대 결과와 대조 | **머지 차단** |
| E2E | 자연어→검증 CAD 전체 | 시나리오 스크립트 | nightly |

### 5.1 골든 케이스 (엔지니어링 정확성의 핵심)
- 검증된 부품(엔진 브래킷 등)의 **입력·기대 형상·기대 FEM 결과(허용오차)**를 고정.
- 솔버·프롬프트 변경 시 회귀를 즉시 탐지. 결과는 허용오차(±%) 내 비교.
- LLM 비결정성 대응: 형상 자체가 아니라 **검증 통과 여부·핵심 지표**로 판정.

---

## 6. CI/CD 파이프라인

```
push/PR ─► lint(ruff)+type(mypy) ─► unit ─► integration(headless FreeCAD)
        ─► golden-case(허용오차 비교) ─► [main] build ─► deploy/* 패키징
nightly ─► E2E 시나리오 + 성능(루프 반복수·시간) 리포트
```
- 컨테이너로 FreeCAD/CalculiX/OpenFOAM 버전 고정(재현성).
- 무거운 시뮬(CFD/위상최적화)은 nightly 또는 라벨 트리거로 분리.

---

## 7. 비결정성 & LLM 개발 규율
- **프롬프트는 코드처럼 버전관리**(`prompts/` + 변경 이력).
- LLM 출력은 **반드시 스키마 검증**(JSON schema) 후 사용. 실패 시 재시도.
- 생성 코드(FreeCAD Python)는 **샌드박스 실행**(타임아웃·리소스 제한·화이트리스트).
- 평가셋(eval set)으로 프롬프트/모델 변경의 회귀를 정량 추적.

---

## 8. 보안 & 안전 (개발 측면)
- 생성된 Python을 직접 `exec` 금지 → 제한된 FreeCAD 서브프로세스/샌드박스.
- 입력(치수·하중)·출력에 대한 감사 로그(누가·언제·무엇을 생성·검증).
- 물성·표준 데이터는 출처 메타데이터 동반 저장, LLM이 임의 생성 금지.

---

## 9. Definition of Done (DoD)
기능이 "완료"되려면:
- [ ] 단위+통합 테스트 통과, 커버리지 기준 충족
- [ ] 관련 골든 케이스 통과(신규 기능이면 골든 케이스 추가)
- [ ] 검증 기준 변경 시 CAE 엔지니어 승인
- [ ] 프롬프트 변경 시 eval 회귀 확인
- [ ] 문서(DESIGN/해당 변형 문서) 갱신
- [ ] 보안: 샌드박스·출처 메타데이터 준수

---

## 10. 환경 셋업 (개발자 온보딩)
```bash
# 1. 코어 의존성
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"            # pytest, ruff, mypy 포함

# 2. FreeCAD (headless) + CalculiX  — 컨테이너 권장
docker compose -f deploy/dev/docker-compose.yml up -d

# 3. LLM 백엔드 (택1)
#   로컬: ollama pull qwen2.5-coder:32b   (v1/v2)
#   클라우드: export ANTHROPIC_API_KEY=...  (v3)

# 4. 스모크 테스트
pytest tests/golden/test_engine_bracket.py -q
```
