# AutoDesign-LLM

자연어로 자동차 부품을 설계하고, 공학 이론·표준·논문 근거의 사전 검토와
물리 검증(FEM/CFD)을 자동 수행해 **검증된 CAD 파일**을 산출하는 LLM 기반 시스템.

> **상태**: Phase 0~7 + 실 LLM(R1~R7) + Hermes(Nous/Ollama) 백엔드 완료 · 테스트 68 통과 ·
> Hermes 라이브 E2E 검증 성공. 현황/다음 할 일은 [PROGRESS.md](PROGRESS.md).

## 🖱 더블클릭 실행 (macOS, 가장 쉬움)
Finder에서 프로젝트 폴더의 아래 파일을 **더블클릭**하면 바로 실행됩니다 (환경 자동 준비 + 끝나면 보고서 자동 열림):
- **`AutoDesign.command`** — 오프라인 데모 (인터넷/LLM 설치 불필요, 항상 동작)
- **`AutoDesign-LocalLLM.command`** — 100% 로컬 LLM(Ollama)로 실행

> 처음 더블클릭 시 "확인되지 않은 개발자" 경고가 뜨면: 파일 우클릭 → **열기** → **열기**. (1회만)
> Dock에 두려면 `.command` 파일을 Dock으로 드래그하세요.

## ⚡ 빠른 시작 (터미널)
```bash
cd ~/Desktop/Cursor/autodesign-llm
./scripts/setup.sh                              # 1회: 환경 + 테스트
./scripts/run.sh --optimize --report            # 데모(오프라인, mock)
./scripts/run.sh --backend hermes --trace "엔진 브래킷, 5kN, AlSi10Mg, 안전계수 2.0, 피로"
```

### 🖥 100% 로컬 LLM으로 실행 (클라우드/API 키 불필요)
```bash
./scripts/setup-local-llm.sh                    # 1회: Ollama 설치 + 코드모델(qwen2.5-coder:7b) 다운로드
./scripts/run-local.sh --report --trace "엔진 브래킷, 5kN, AlSi10Mg, 안전계수 2.0, 피로"
# 모델 변경(품질↑):  OLLAMA_MODEL=qwen2.5-coder:32b ./scripts/run-local.sh --optimize --report
```
> `run-local.sh`는 venv·Ollama 서버·모델 누락분을 자동으로 채운 뒤 `--backend local`로 실행합니다.
> 설계 치수·하중 데이터가 외부로 나가지 않아 IP 보안에 유리합니다.

전체 셋업·운영·다음 단계 가이드 → **[docs/08-DEV-SETUP.md](docs/08-DEV-SETUP.md)**

## 폴더 구성
```
autodesign-llm/
├── README.md              ← 본 파일
├── AutoDesign-LLM_요약.pptx  ★ 전체 요약 발표자료 (16장, 구성도 포함)
├── DESIGN.md              시스템 설계 (구조 부품 + 외형 툴체인)
├── docs/                  개발 문서 (Markdown)
│   ├── 00-INDEX.md            문서 인덱스 + 세 버전 관계
│   ├── 01-ROADMAP.md          [기획자] 전체 개발 로드맵
│   ├── 02-DEV-PROCESS.md      [개발자] 개발 프로세스
│   ├── 03-VARIANT-LOCAL.md    배포 v1: 로컬 LLM
│   ├── 04-VARIANT-HYBRID.md   배포 v2: 로컬+RAG 하이브리드 (주력)
│   └── 05-VARIANT-CLOUD.md    배포 v3: 클라우드
├── PROGRESS.md            ★ 구현 진행 현황 (Phase 0 완료, 다음 단계)
├── src/autodesign/        ★ 코어 구현 코드 (Phase 0~7)
│   ├── spec.py                ① 설계명세(DesignSpec)
│   ├── llm/                   ② LLM 추상화 + Mock 백엔드
│   ├── geometry/              ③ 파라메트릭 브래킷 (FreeCAD 지연연결)
│   ├── validation/            ④ 검증: 기하·구조(솔버)·DFM·피로·모달
│   ├── orchestrator/          ⑤ 생성→검증→자기교정 루프
│   ├── knowledge/             RAG 지식베이스 + 사전검토 (Phase 3)
│   ├── optimization/          경량화 최적화 (Phase 5)
│   ├── exterior/              외형 개념→공력 루프 (Phase 6)
│   ├── reporting/             검토보고서 HTML/PDF (Phase 4)
│   ├── api.py                 통합 API 파사드 (Phase 7)
│   └── cli.py                 데모 실행
├── tests/                 테스트 (26 passed)
├── samples/               샘플 검토보고서(HTML/PDF)
├── pyproject.toml
├── word/                  ★ 위 문서의 Word(.docx) 버전 (구성도 이미지 포함)
├── assets/                시스템 구성도 이미지(PNG) + 생성 스크립트
│   ├── diagram_system_overview.png
│   ├── diagram_variants.png
│   ├── diagram_v1_local.png / v2_hybrid / v3_cloud.png
│   ├── make_diagrams.py       다이어그램 생성 스크립트
│   └── md_to_docx.py          Markdown→Word 변환 스크립트
```

## 읽는 순서 (권장)
1. `DESIGN.md` — 무엇을 만드는가 (아키텍처)
2. `docs/01-ROADMAP.md` — 언제·어떤 순서로 (기획)
3. `docs/02-DEV-PROCESS.md` — 어떻게 개발하는가
4. `docs/03~05` — 배포 버전별 상세 계획

## 코어 실행 (Phase 0~7 — 의존성 없이 동작)
```bash
pip3 install --user pytest
# 구조 부품: 자연어 → 명세 → 사전검토(RAG) → 생성·검증·자기교정 → 경량화 → 보고서
PYTHONPATH=src python3 -m autodesign.cli --optimize --report
# 외형(공력): 개념 생성 → 공력 검증 → 교정 루프
PYTHONPATH=src python3 -m autodesign.cli --exterior
# 테스트
PYTHONPATH=src python3 -m pytest tests/ -q          # 26 passed
```
> FreeCAD/CalculiX/OpenFOAM 미설치 시 dry-run(해석적) 모드로 전체 워크플로를 시연.
> 설치 시 솔버 주입만으로 실연결. 진행 현황·남은 작업은 `PROGRESS.md`.

## 문서 재생성 방법
```bash
pip3 install --user python-docx matplotlib
python3 assets/make_diagrams.py     # 구성도 PNG 재생성
python3 assets/md_to_docx.py        # Word 문서 재생성
python3 assets/build_pptx.py        # 요약 PPTX 재생성
```

- 작성일: 2026-06-09 / 상태: 설계·기획 + Phase 0 구현 완료
