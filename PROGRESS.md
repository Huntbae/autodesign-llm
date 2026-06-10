# 구현 진행 현황 (차례대로)

개발 순서: docs/02-DEV-PROCESS.md §3. 로드맵 Phase: docs/01-ROADMAP.md.
검증: 68 passed. **Phase 0~7 + 실 LLM(R1~R7) + Hermes(Nous/Ollama) 백엔드 완료.**
★ 라이브 E2E 검증 성공(2026-06-10): 실제 LLM(Nous, 무료모델)로 파싱→RAG 사전검토→
LLM 설계제안(σ=6FL/Wt² 직접 계산, 두께 18.3mm 도출)→검증 게이트 전부 통과→1회 수렴.
모델 ID `nousresearch/hermes-4-70b`(유료, 크레딧 필요). 무료모델로 전체 흐름 실증 완료.

## ✅ Phase 0 — 기반 구축 (완료)
| 순서 | 모듈 | 파일 | 상태 |
|------|------|------|------|
| ① | 설계명세 스키마 | `src/autodesign/spec.py` | ✅ |
| ② | LLM 추상화 + Mock 백엔드 | `src/autodesign/llm/` | ✅ |
| ③ | 파라메트릭 형상(브래킷) | `src/autodesign/geometry/` | ✅ |
| ④ | 검증 게이트 | `src/autodesign/validation/` | ✅ |
| ⑤ | 생성→검증→자기교정 루프 | `src/autodesign/orchestrator/` | ✅ |

## ✅ Phase 1 — 형상 생성 MVP (코드 완료, FreeCAD는 설치 환경에서)
- ✅ 볼트 홀(장착점) + 필렛 형상 — `geometry/bracket.py`
- ✅ DFM(제조성) 검증: 최소 벽두께·필렛·홀 모서리 여유 — `validation/dfm.py`
- ✅ **CAD 파일 산출 배선** — `BracketModel.export()`(STEP+FCStd) + `api.design_part(cad=True)`가
  수렴된 **최종(경량화 반영) 모델**을 자동 export. CLI에 `[CAD]`/생성 경로 출력 — `geometry/bracket.py`, `api.py`
- ⏳ FreeCAD 실연결(STEP/FCStd) — 배선 완료, **FreeCAD 설치 시 실제 파일 자동 생성**
  (이 환경엔 FreeCAD/conda 없음 → dry-run 안내 + 미설치 시 우아하게 건너뜀)

## ✅ Phase 2 — 구조 검증 추상화 (FEM 교체 준비 완료)
- ✅ `StructuralSolver` 인터페이스로 솔버 분리 — `validation/structural.py`
- ✅ `AnalyticBendingSolver`(현재 기본, 보수적 근사)
- ✅ `CalculiXSolver` 어댑터 스캐폴드(미설치 시 해석적 폴백, 설치 시 FEM 자리)
- ⏳ CalculiX 실제 메시·해석 파이프라인 = Phase 2 후속 TODO(설치 환경)

## ✅ Phase 3 — 지식(RAG) 골격 (완료)
- ✅ 의존성 없는 TF-IDF 검색기 + 출처 메타 청크 — `knowledge/`
- ✅ 지식베이스: 재료·설계규칙(출처 표기) — `knowledge/data/*.json`
- ✅ 인용 기반 사전 검토 리포트 + 자리표시자 물성 ⚠️ 경고 — `knowledge/prereview.py`
- ⏳ 임베딩+벡터DB 교체, **검증된 물성·표준 데이터로 교체**(현재 자리표시자)

## ✅ Phase 4 — 피로 검증 + 검토보고서 (완료)
- ✅ 피로 S-N 근사 + 수명 추정 — `validation/fatigue.py`
- ✅ 검증 게이트에 피로 추가, 자기교정이 강도·피로 동시 만족(지배 제약 채택)
- ✅ 검토보고서: **HTML 항상 + PDF(reportlab, 한글폰트 등록)** — `reporting/`
- ✅ 샘플: `samples/sample_review_report.{html,pdf}`
- ⏳ 피로 평균응력 보정·다축·Miner 다중하중, FEM 응력장 기반 = 후속(설치 환경)

## ✅ Phase 5 — 경량화 최적화 (완료)
- ✅ 두께×포켓 파라미터 스윕으로 검증 만족 중 최소 질량 탐색 — `optimization/lightweight.py`
- ✅ 데모: 질량 **81g→46g (43% 감소)** & 전 검증 통과 (목표 ≥15% 충족)
- ⏳ 실제 위상최적화(SIMP/BESO + FEM)로 교체 = 설치 환경 후속

## ✅ Phase 6 — 외형 툴체인 (골격 완료)
- ✅ 개념 생성→공력 검증→교정 루프(구조와 동일 패턴, 검증축=Cd) — `exterior/`
- ✅ `AnalyticDragSolver`(해석적 Cd) / `OpenFOAMSolver` 어댑터(미설치 시 폴백)
- ✅ 데모: Cd 0.33→0.29 수렴
- ⏳ TRELLIS/Hunyuan3D(개념 메시), OpenFOAM(실 CFD), 메시→NURBS = 설치 환경 후속

## ✅ Phase 7 — 통합 API/제품 파사드 (완료)
- ✅ `api.design_part()` / `api.design_exterior()` — 파싱→사전검토→루프→경량화→보고서 일괄
- ✅ CLI: `--optimize`, `--report`, `--exterior`

### 실행
```bash
PYTHONPATH=src python3 -m autodesign.cli --optimize --report   # 구조+경량화+보고서
PYTHONPATH=src python3 -m autodesign.cli --exterior            # 외형 공력 루프
PYTHONPATH=src python3 -m pytest tests/ -q                     # 26 passed
```

## ✅ 실제 LLM 기반 (R1~R5 완료) — docs/06-REAL-LLM-BUILD.md
- ✅ LLM 추상 베이스 + JSON 스키마 강제·재시도 — `llm/json_llm.py`, `llm/json_utils.py`
- ✅ **Claude 백엔드** (claude-opus-4-8, adaptive thinking, 구조화 출력) — `llm/cloud_backend.py`
- ✅ **로컬 Ollama 백엔드** (urllib, format=스키마) — `llm/local_backend.py`
- ✅ **Hermes(Nous) 백엔드** — 사용자 `~/.hermes` 추론 API(OpenAI 호환, Hermes-4) — `llm/nous_backend.py`. `--backend hermes`/`nous`
- ✅ **Hermes(Ollama) 백엔드** — 오프라인 `hermes3` — `llm/hermes_backend.py`, `llm/hermes.py`. `--backend ollama-hermes` · docs/07
- 🔒 보안: Hermes 토큰은 런타임에만 로드, 외부 전송 안 함(개발 중 토큰 외부전송 차단됨)
- ✅ 백엔드 팩토리 + CLI `--backend mock|cloud|local|auto` — `llm/factory.py`
- ✅ **코드생성(방식 B) 안전화**: AST 화이트리스트 + 서브프로세스 샌드박스 — `geometry/codegen.py`
- ✅ 프롬프트 자산화 — `llm/prompts.py`
- ✅ **R6 평가셋·회귀** — `eval/` (러너 채점: 파싱 정확도·루프 통과율). `--eval`로 회귀 탐지
- ✅ **R7 관측·캐싱** — `llm/observe.py`(지연·성공/실패 기록, JSONL), cloud 시스템 prefix 캐싱
- ✅ 네트워크 없는 통합 테스트(transport/가짜 클라이언트/평가/관측) 23종

### 실행 (실 LLM)
```bash
export ANTHROPIC_API_KEY=...; pip install anthropic
PYTHONPATH=src python3 -m autodesign.cli --backend cloud --report --trace "..."
PYTHONPATH=src python3 -m autodesign.cli --eval --backend cloud   # 회귀 평가
# 로컬: ollama serve + ollama pull qwen2.5-coder:32b → --backend local
```

## ⏭ 남은 실연결 (외부 도구 설치 필요)
1. **검증된 물성·표준 데이터 확보** → `MATERIALS`·KB 자리표시자 교체 (최우선)
2. **FreeCAD/CalculiX**: 실 솔리드(STEP) + FEM 응력장 → 해석적 솔버 대체
3. **OpenFOAM + Blender/TRELLIS**: 실 CFD + 개념 메시 → 외형 해석적 대체
4. **위상최적화(SIMP)**: 파라미터 스윕 → 진짜 토폴로지 최적화
5. **UI/배포**: 웹 UI, v1/v2/v3 배포 패키징

## ⚠️ 현재 한계 (명시)
- 물성·설계기준 값은 **자리표시자** — 안전 판정에 그대로 쓰지 말 것.
- 구조/모달은 **해석적 근사**(교육용). 실제 판정은 FEM(CalculiX) 필요.
- 시스템은 보조 도구. 최종 양산 판정은 정식 CAE·실물시험 필수.
