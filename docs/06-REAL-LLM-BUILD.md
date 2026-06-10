# 06. 실제 LLM 기반 CAD 생성 시스템 구축 프로세스 & 개발 계획서

> Mock을 **진짜 LLM**(Claude API / 로컬 Ollama)으로 교체하고, LLM이 직접 설계·CAD를
> 생성하도록 만드는 구축 프로세스와 단계별 개발 계획.

- 버전: v0.1 / 작성일: 2026-06-10

---

## 1. 무엇이 "실제 LLM 기반"인가

기존 코어는 `MockLLM`(결정적 휴리스틱)으로 루프를 시연했다. 실제 시스템은 동일한
`LLMClient` 계약을 **진짜 모델**로 구현한다. 모델은 두 가지 방식으로 CAD를 만든다:

| 방식 | 산출 | 장점 | 위험 | 사용처 |
|------|------|------|------|--------|
| **A. 파라미터 생성** | 구조화 JSON(두께·필렛 등) | 안전·결정적, 검증 쉬움 | 표현력 한정 | 골든 부품(브래킷) |
| **B. 코드 생성** | FreeCAD Python 스크립트 | 임의 형상 표현 | 임의코드 실행 위험 | 복잡/신규 형상 |

→ **A를 기본**, B는 **샌드박스 + AST 화이트리스트**로 통제하며 점진 확대.

```
자연어 → LLM(파싱) → 설계명세 → [RAG 사전검토]
       → LLM(생성: 파라미터 or FreeCAD 코드) → (샌드박스) 실행
       → 검증 게이트(FEM/DFM/피로) → 실패 시 LLM 자기교정 → 산출물+보고서
```

---

## 2. 구축 프로세스 (LLM 통합 관점)

1. **계약 고정** — `LLMClient`(parse_spec/propose/correct) + 출력 **JSON 스키마**.
2. **백엔드 구현** — Claude(클라우드) / Ollama(로컬). 동일 계약, 교체 가능.
3. **구조화 출력 강제** — Claude `output_config.format`(json_schema), Ollama `format`.
   스키마 위반 시 **재시도 루프**(오류를 모델에 되먹임).
4. **프롬프트 자산화** — 시스템 프롬프트·few-shot을 `prompts.py`에 버전관리.
5. **코드생성 안전화** — 생성 스크립트는 **AST 화이트리스트** 통과 후 **서브프로세스
   샌드박스**(freecadcmd)에서만 실행. `os/sys/subprocess/open/eval/exec/__import__` 금지.
6. **평가셋(eval)** — 자연어→기대 명세/검증결과 쌍으로 회귀 측정(프롬프트·모델 변경 가드).
7. **관측·비용** — 토큰·실패·교정횟수 로깅, 캐싱(시스템 프롬프트 prefix).

---

## 3. 단계별 개발 계획 (R1~R7)

| 단계 | 목표 | 산출물 | 완료 기준 |
|------|------|--------|-----------|
| **R1** | LLM 추상화 + JSON 유틸 | `json_llm.py`, `json_utils.py` | 스키마 검증·재시도 동작 |
| **R2** | Claude 백엔드 | `cloud_backend.py` | API로 parse/propose/correct |
| **R3** | 로컬 백엔드 | `local_backend.py` | Ollama로 동일 동작 |
| **R4** | 백엔드 팩토리 + CLI | `factory.py`, `--backend` | mock/cloud/local 전환 |
| **R5** | 코드생성 + 샌드박스 | `geometry/codegen.py` | AST 거부/허용, 샌드박스 실행 |
| **R6** | 평가셋·회귀 | `tests/eval/` | 프롬프트 변경 회귀 탐지 |
| **R7** | 비용·캐싱·관측 | 로깅·prefix 캐시 | 토큰/실패 대시보드 |

> 본 커밋 범위: **R1~R5**(오프라인 검증 가능 — 실 API/Ollama/FreeCAD는 설치 시 자동 연결).

---

## 4. 기술 사양 (claude-api 기준)

| 항목 | 값 |
|------|-----|
| 모델 | `claude-opus-4-8` (기본) |
| 사고 | `thinking={"type":"adaptive"}` + `output_config={"effort":"high"}` |
| 구조화 출력 | `output_config={"format":{"type":"json_schema","schema":...}}` |
| 금지 | `temperature/top_p/top_k`, `budget_tokens` (Opus 4.8에서 400) |
| SDK | `pip install anthropic`; `anthropic.Anthropic()` (ANTHROPIC_API_KEY) |
| 로컬 | Ollama `http://localhost:11434/api/chat`, `format`=JSON 스키마, 코드특화 모델 |

배포 버전 매핑: **v1 로컬**=`local_backend`, **v3 클라우드**=`cloud_backend`,
**v2 하이브리드**=로컬 백엔드 + RAG(knowledge) + (옵션) 클라우드 버스트.

---

## 5. 보안·안전 (필수)

- **임의코드 미실행**: 생성 Python은 AST 화이트리스트 통과분만, 격리 서브프로세스에서.
- **민감 데이터**: v1/v2는 온프레미스(설계 IP 외부 미전송). v3는 no-retention 정책.
- **출처 강제**: 물성·표준 수치는 RAG 근거(인용). 모델이 임의 생성한 수치는 거부.
- **안전 고지**: 산출물은 보조. 양산 판정은 정식 CAE·실물시험.

---

## 6. 실행 (구축 후)
```bash
# 클라우드(Claude)
export ANTHROPIC_API_KEY=...   ; pip install anthropic
PYTHONPATH=src python3 -m autodesign.cli --backend cloud --report "..."
# 로컬(Ollama)
ollama serve & ; ollama pull qwen2.5-coder:32b
PYTHONPATH=src python3 -m autodesign.cli --backend local "..."
# 오프라인(mock, 기본)
PYTHONPATH=src python3 -m autodesign.cli "..."
```
