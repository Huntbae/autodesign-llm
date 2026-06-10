# 08. 맥북프로에서 이어서 개발하기 (셋업 · 운영 · 다음 단계)

> 이 문서 하나로 환경 구축부터 일상 명령, 다음 작업까지 이어갈 수 있다.

- 작성일: 2026-06-10 / 대상: macOS (Apple Silicon/Intel)

---

## 1. 한 번만 — 셋업
```bash
cd ~/Desktop/Cursor/autodesign-llm
./scripts/setup.sh          # .venv 생성 + 의존성 + 스모크 테스트(68 passed)
```
> Python 3.9+ 필요(맥 기본 python3 사용 가능). 코어는 의존성 0 — pytest만 dev로 설치.
> 문서 생성(다이어그램/Word/PPTX/PDF)을 쓰려면 matplotlib·python-docx·python-pptx·reportlab도
> 함께 설치됨(setup.sh가 자동, 실패해도 코드 동작엔 무관).

## 2. 매일 — 자주 쓰는 명령
```bash
./scripts/test.sh                       # 전체 테스트
./scripts/run.sh --optimize --report    # 구조부품: 설계→검증→경량화→보고서 (오프라인 mock)
./scripts/run.sh --exterior             # 외형(공력) 루프
./scripts/run.sh --eval                 # 회귀 평가(파싱·루프 점수)
./scripts/build-docs.sh                 # 구성도·Word·PPTX 재생성
```
직접 실행(스크립트 없이):
```bash
source .venv/bin/activate
PYTHONPATH=src python -m autodesign.cli "엔진 브래킷, 5kN, AlSi10Mg, 안전계수 2.0, 피로"
```

## 3. 실제 LLM 백엔드
| 백엔드 | 명령 | 준비 |
|--------|------|------|
| mock(오프라인) | `./scripts/run.sh "..."` | 없음(기본) |
| **Hermes(Nous)** | `./scripts/run.sh --backend hermes --trace "..."` | `~/.hermes` 로그인. 유료모델은 크레딧 필요 |
| 무료모델로 검증 | `HERMES_MODEL=stepfun/step-3.7-flash:free ./scripts/run.sh --backend hermes "..."` | 크레딧 불필요 |
| Claude(클라우드) | `./scripts/run.sh --backend cloud "..."` | `pip install anthropic` + `ANTHROPIC_API_KEY` |
| Ollama Hermes | `./scripts/run.sh --backend ollama-hermes "..."` | `ollama serve` + `ollama pull hermes3` |

- Hermes 토큰 만료 시: `hermes auth add nous` 재로그인 (자세히 docs/07).
- Hermes-4 정식 사용: portal.nousresearch.com 크레딧 충전 → `nousresearch/hermes-4-70b`.

## 4. 무엇이 어디에 있나
```
autodesign-llm/
├── README.md            프로젝트 front door
├── PROGRESS.md          ★ 현재까지/다음 할 일 (가장 먼저 볼 것)
├── DESIGN.md            시스템 설계
├── docs/                기획·개발·배포·LLM·셋업 문서 (00~08)
├── src/autodesign/      코어 코드 (41 모듈)
├── tests/               테스트 (68)
├── assets/              구성도 PNG + 생성 스크립트
├── word/                문서의 Word 버전
├── samples/             샘플 검토보고서(HTML/PDF)
├── scripts/             setup/run/test/build-docs
└── AutoDesign-LLM_요약.pptx  발표자료
```
읽는 순서: `PROGRESS.md` → `docs/00-INDEX.md` → `docs/01-ROADMAP.md` → 해당 모듈 코드.

## 5. 코드 구조(어디를 고치나)
| 하고 싶은 것 | 파일 |
|--------------|------|
| 새 부품 종류 추가 | `geometry/`, `validation/`, `optimization/` |
| 검증 기준/솔버 교체(FEM) | `validation/structural.py`(CalculiX 자리), `validation/fatigue.py` |
| 물성·표준 데이터 | `knowledge/data/*.json` (⚠️ 자리표시자 교체) |
| 프롬프트 수정 | `llm/prompts.py` |
| 새 LLM 백엔드 | `llm/*_backend.py` + `llm/factory.py` |
| 외형(공력) | `exterior/` |

## 6. 다음 단계 (우선순위)
1. **검증된 물성·표준 데이터 확보** → `spec.MATERIALS`·`knowledge/data` 자리표시자 교체 (안전 직결, 최우선)
2. **FreeCAD/CalculiX 설치** → `geometry/runner.py`·`validation/structural.py`로 실제 STEP/FEM 연결
   - 설치: `conda install -c conda-forge freecad` 또는 FreeCAD.app
3. **Hermes-4 크레딧 충전** → 고품질 실 LLM 설계 (코드는 이미 준비됨)
4. **R6 평가셋 확장 / R7 비용·캐싱 대시보드**
5. (장기) 외형 Class-A, 웹 UI, v1/v2/v3 배포 패키징

## 7. 버전 관리 (이어가기)
이 폴더는 git 저장소로 초기화되어 있다.
```bash
git status
git add -A && git commit -m "작업 내용"
# 원격 연결 시: git remote add origin <repo-url> && git push -u origin main
```

## 8. 트러블슈팅
| 증상 | 해결 |
|------|------|
| `ModuleNotFoundError: autodesign` | `PYTHONPATH=src` 또는 `./scripts/run.sh` 사용 |
| `No module named anthropic` | cloud 백엔드용 — `pip install anthropic` |
| Ollama 연결 실패 | `ollama serve` 실행 여부 확인 |
| Hermes 토큰 만료 | `hermes auth add nous` |
| Hermes 404 credits | portal.nousresearch.com 크레딧 충전 또는 무료모델 사용 |
| FreeCAD 미설치 | dry-run(해석적)으로 동작 — 실제 솔리드/FEM은 설치 후 |
