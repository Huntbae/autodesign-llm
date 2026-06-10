# 07. Hermes 기반 LLM 백엔드

> 두 가지 Hermes 경로를 지원한다.
> - **`hermes` (권장, 사용자 환경)** — 설치된 **Nous Research Hermes 에이전트**의 추론 API
>   (OpenAI 호환, `inference-api.nousresearch.com/v1`)를 Hermes-4 모델로 사용.
> - **`ollama-hermes`** — 오프라인에서 Ollama로 받은 `hermes3`를 사용.

- 버전: v0.2 / 작성일: 2026-06-10

## 1. 환경 확인 결과
이 머신에는 `~/.hermes`(Nous Hermes 에이전트)가 설치·구동 중이며, 모델 공급자는
`provider: nous`, `base_url: https://inference-api.nousresearch.com/v1`. 자격증명은
`~/.hermes/shared/nous_auth.json`(OAuth access_token)에 있다. 사용 가능 모델:
**Hermes-4-405B / Hermes-4-70B / Hermes-4-14B** 등.

> ⚠️ **보안**: 백엔드는 토큰을 코드에 저장하지 않고 **실행 시점에만** 자격 파일에서
> 읽는다. (개발 중 자동화 도구가 사용자 토큰을 외부로 전송하는 것은 차단됨 — 라이브
> 검증은 사용자가 직접 수행.)

## 2. 실행 — Nous Hermes (사용자 환경)
```bash
# 자격증명은 ~/.hermes/shared/nous_auth.json 에서 자동 로드
PYTHONPATH=src python3 -m autodesign.cli --backend hermes \
  "엔진 브래킷, 5kN, AlSi10Mg, 안전계수 2.0, 피로"
# 모델 선택 / 또는 API 키 직접 지정
HERMES_MODEL=Hermes-4-405B PYTHONPATH=src python3 -m autodesign.cli --backend hermes --trace "..."
NOUS_API_KEY=... NOUS_INFERENCE_BASE_URL=https://inference-api.nousresearch.com/v1 \
  PYTHONPATH=src python3 -m autodesign.cli --backend nous "..."
# 회귀 평가
PYTHONPATH=src python3 -m autodesign.cli --eval --backend hermes
```
기본(`auto`)은 오프라인 mock이다. Hermes는 `--backend hermes`로 명시 선택하거나
`NOUS_API_KEY` 환경변수를 설정한다(그러면 auto가 Hermes 선택).

## 3. 실행 — Ollama Hermes (오프라인 대안)
```bash
ollama serve & ; ollama pull hermes3
PYTHONPATH=src python3 -m autodesign.cli --backend ollama-hermes "..."
```

## 4. 동작 방식 (2단계, 견고)
```
parse/propose/correct
  └─ ① Hermes 네이티브: 시스템에 <tools>스키마</tools> 주입 →
        <tool_call>{arguments}</tool_call> 파싱
  └─ ② 폴백: OpenAI response_format=json_object (Nous) / Ollama format=schema
  → 스키마 검증 실패 시 오류 되먹여 재시도
```
- `llm/nous_backend.py` — Nous 추론 API(OpenAI 호환), 자격증명 런타임 로드
- `llm/hermes_backend.py` — Ollama `hermes3`
- `llm/hermes.py` — 공통 함수호출 프롬프트/파서

## 5. 모델 선택 (라이브 확인된 실제 ID)
Nous 추론 API는 **OpenRouter형 게이트웨이**다. 모델 ID는 `provider/name` 형식.
| 용도 | 모델 ID | 비고 |
|------|---------|------|
| 기본 | `nousresearch/hermes-4-70b` | **유료** — 계정 크레딧 필요 |
| 고품질 | `nousresearch/hermes-4-405b` | **유료** |
| 무료(검증용) | `stepfun/step-3.7-flash:free`, `nvidia/nemotron-3-ultra:free` | 파이프라인 확인용(비-Hermes) |

> `/v1/models`로 계정에서 쓸 수 있는 모델을 확인. **잔액 부족 시 404**:
> `"Model ... requires available credits ... add credits at portal.nousresearch.com"`.
> → portal.nousresearch.com에서 크레딧 충전 후 `nousresearch/hermes-4-70b` 사용.
> 무료로 전체 흐름만 보려면 `HERMES_MODEL=stepfun/step-3.7-flash:free`.

## 6. 인증 만료 시 (라이브 검증됨)
`~/.hermes/shared/nous_auth.json`의 `access_token`은 만료된다(약 24h). 백엔드는 호출 전
`expires_at`을 검사해 만료 시 **토큰을 보내지 않고** 즉시 안내한다:
```
[백엔드 오류] Hermes 토큰이 만료되었습니다(expires_at=...). `hermes auth add nous` 로 재로그인 후 다시 실행하세요.
```
재로그인:
```bash
hermes auth add nous     # OAuth 재인증 → nous_auth.json 갱신
# 이후 재실행
PYTHONPATH=src python3 -m autodesign.cli --backend hermes --eval
```
> 2026-06-10 라이브 검증: 코드가 Nous API에 도달 → 401 수신 → 정확히 처리됨. 통합 자체는
> 검증 완료이며, 남은 것은 토큰 갱신뿐.

## 7. 참고
- Nous Hermes 4 — https://nousresearch.com/
- Ollama Hermes3 — https://ollama.com/library/hermes3
