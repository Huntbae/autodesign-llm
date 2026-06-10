"""Nous Research Hermes 백엔드 — 사용자의 Hermes 추론 API(OpenAI 호환) 사용.

`~/.hermes`(Hermes 에이전트 런타임)가 설치된 환경에서, OpenAI 호환 추론 엔드포인트
(inference-api.nousresearch.com/v1)에 Hermes 모델로 요청한다. 자격증명은 실행 시점에
사용자의 `~/.hermes/shared/nous_auth.json`(또는 NOUS_API_KEY)에서 읽는다.

보안: 토큰은 런타임에만 로드되며, 코드 자체에 저장하지 않는다. 구조화 출력은 Hermes
네이티브 `<tool_call>` 포맷을 우선 사용하고, OpenAI `response_format=json_object`로 폴백.
"""
from __future__ import annotations

import datetime
import json
import os
import urllib.error
import urllib.request
from typing import Callable, Optional, Tuple

from .hermes import build_tool_system, parse_tool_call
from .json_llm import JsonLLMBase
from .json_utils import extract_json

DEFAULT_AUTH = os.path.expanduser("~/.hermes/shared/nous_auth.json")
DEFAULT_BASE = "https://inference-api.nousresearch.com/v1"
DEFAULT_MODEL = "nousresearch/hermes-4-70b"   # Nous(OpenRouter형) ID. 또한: nousresearch/hermes-4-405b


RELOGIN_HINT = "`hermes auth add nous` 로 재로그인 후 다시 실행하세요."


def _load_creds(base_url, token, auth_path) -> Tuple[str, Optional[str], str, Optional[str]]:
    """(base_url, token, token_type, expires_at) 해석. 구성 시점엔 실패하지 않음."""
    if token:
        return (base_url or DEFAULT_BASE), token, "Bearer", None
    key = os.getenv("NOUS_API_KEY")
    if key:
        return (base_url or os.getenv("NOUS_INFERENCE_BASE_URL") or DEFAULT_BASE), key, "Bearer", None
    try:
        with open(auth_path, encoding="utf-8") as f:
            d = json.load(f)
        return (base_url or d.get("inference_base_url") or DEFAULT_BASE,
                d.get("access_token"), d.get("token_type", "Bearer"), d.get("expires_at"))
    except Exception:
        return (base_url or DEFAULT_BASE), None, "Bearer", None


def _is_expired(expires_at: Optional[str]) -> bool:
    if not expires_at:
        return False
    try:
        e = datetime.datetime.fromisoformat(str(expires_at).replace("Z", "+00:00"))
        return datetime.datetime.now(datetime.timezone.utc) > e
    except Exception:
        return False


class NousHermesLLM(JsonLLMBase):
    def __init__(self, *, model: Optional[str] = None, base_url: Optional[str] = None,
                 token: Optional[str] = None, auth_path: str = DEFAULT_AUTH,
                 post: Optional[Callable] = None, max_tokens: int = 4000,
                 timeout: float = 120.0, expires_at: Optional[str] = None, **kw):
        super().__init__(**kw)
        self.base_url, self.token, self.token_type, exp = _load_creds(base_url, token, auth_path)
        self.expires_at = expires_at or exp
        self.model = model or os.getenv("HERMES_MODEL") or DEFAULT_MODEL
        self.max_tokens = max_tokens
        self.timeout = timeout
        self._post = post   # 주입식 HTTP seam(테스트): (payload:dict) -> content:str

    # ---- OpenAI 호환 chat/completions ----
    def _chat(self, system: str, user: str, response_format: Optional[dict] = None) -> str:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "max_tokens": self.max_tokens,
            "stream": False,
        }
        if response_format:
            payload["response_format"] = response_format
        if self._post is not None:
            return self._post(payload)

        if not self.token:
            raise RuntimeError(
                "Hermes(Nous) 인증 토큰을 찾을 수 없습니다. " + RELOGIN_HINT
                + " (오프라인은 --backend mock)"
            )
        if _is_expired(self.expires_at):
            raise RuntimeError(
                f"Hermes 토큰이 만료되었습니다(expires_at={self.expires_at}). " + RELOGIN_HINT
            )
        req = urllib.request.Request(
            self.base_url.rstrip("/") + "/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json",
                     "Authorization": f"{self.token_type} {self.token}"},
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                body = json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 401:
                raise RuntimeError("Hermes 토큰 만료/무효 — Hermes 재로그인이 필요합니다.") from e
            raise RuntimeError(f"Nous 추론 API 오류 {e.code}: {e.reason}") from e
        except urllib.error.URLError as e:
            raise RuntimeError(f"Nous 추론 API 연결 실패: {e.reason}") from e
        msg = (body.get("choices") or [{}])[0].get("message", {})
        # content가 null인 모델(thinking형) 대비: reasoning 필드 폴백
        return msg.get("content") or msg.get("reasoning_content") or msg.get("reasoning") or ""

    # ---- 구조화 출력 ----
    def _raw_json(self, system: str, user: str, schema: dict) -> dict:
        # 1) Hermes 네이티브 함수호출
        try:
            content = self._chat(build_tool_system(system, schema), user)
            data = parse_tool_call(content)
            if isinstance(data, dict) and data:
                return data
        except RuntimeError:
            raise           # 인증/연결 오류는 그대로 노출
        except Exception:
            pass
        # 2) 폴백: OpenAI JSON 모드
        return extract_json(self._chat(system, user, response_format={"type": "json_object"}))

    def _raw_text(self, system: str, user: str) -> str:
        return self._chat(system, user)
