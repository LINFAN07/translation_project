"""
Gemini API：單次設定金鑰、可重試的 generate_content、盡力擷取文字（含多部分候選）。
"""
from __future__ import annotations

import os
import time
from typing import Any

import google.generativeai as genai
from dotenv import load_dotenv

from gemini_worker_client import worker_base_url, worker_generate_with_retries

load_dotenv()

try:
    from google.api_core import exceptions as google_api_exceptions
except ImportError:  # pragma: no cover
    google_api_exceptions = None

_RETRY_EXCEPTION_TYPES: tuple[type[BaseException], ...] = ()
if google_api_exceptions is not None:
    _RETRY_EXCEPTION_TYPES = tuple(
        t
        for t in (
            getattr(google_api_exceptions, "ResourceExhausted", None),
            getattr(google_api_exceptions, "ServiceUnavailable", None),
            getattr(google_api_exceptions, "DeadlineExceeded", None),
            getattr(google_api_exceptions, "InternalServerError", None),
        )
        if t is not None
    )

_configured_for_key: str | None = None


def ensure_genai_configured(api_key: str | None = None) -> None:
    """同一行程只對同一支金鑰呼叫 configure 一次。"""
    global _configured_for_key
    key = (api_key or os.getenv("GEMINI_API_KEY") or "").strip()
    if not key:
        raise ValueError("需要 GEMINI_API_KEY（環境變數或參數）。")
    if _configured_for_key != key:
        genai.configure(api_key=key)
        _configured_for_key = key


def _is_retryable(exc: BaseException) -> bool:
    msg = str(exc).lower()
    if any(
        x in msg
        for x in (
            "429",
            "resource exhausted",
            "quota",
            "rate limit",
            "503",
            "500",
            "unavailable",
            "deadline",
            "timeout",
        )
    ):
        return True
    if _RETRY_EXCEPTION_TYPES and isinstance(exc, _RETRY_EXCEPTION_TYPES):
        return True
    return False


def _extract_text_from_response(response: Any) -> str | None:
    if response is None:
        return None
    try:
        t = response.text
        if t and str(t).strip():
            return str(t).strip()
    except (ValueError, AttributeError):
        pass
    try:
        cands = getattr(response, "candidates", None) or []
        if not cands:
            return None
        content = getattr(cands[0], "content", None)
        if not content:
            return None
        parts = getattr(content, "parts", None) or []
        texts: list[str] = []
        for p in parts:
            tx = getattr(p, "text", None)
            if tx:
                texts.append(str(tx))
        joined = "".join(texts).strip()
        return joined or None
    except (AttributeError, IndexError, TypeError):
        return None


def generate_text(
    model_name: str,
    prompt: str,
    *,
    api_key: str | None = None,
    max_retries: int = 5,
    base_delay_sec: float = 1.5,
) -> str:
    """
    呼叫 Gemini 並回傳純文字。遇可重試錯誤或空回應會指數退避重試；仍失敗則丟出最後例外。

    若設定環境變數 GEMINI_WORKER_URL，改經 Cloudflare Worker 代理（Google 金鑰只存在 Worker Secrets）。
    """
    if worker_base_url():
        return worker_generate_with_retries(
            model_name,
            prompt,
            max_retries=max_retries,
            base_delay_sec=base_delay_sec,
        )
    ensure_genai_configured(api_key)
    model = genai.GenerativeModel(model_name)
    last_exc: BaseException | None = None
    for attempt in range(max_retries):
        try:
            response = model.generate_content(prompt)
            text = _extract_text_from_response(response)
            if text:
                return text
            last_exc = RuntimeError(
                "模型未回傳可用文字（可能遭安全審查阻擋或回應為空）。"
            )
        except Exception as e:  # noqa: BLE001
            last_exc = e
            if not _is_retryable(e):
                raise
        if attempt < max_retries - 1:
            time.sleep(base_delay_sec * (2**attempt))
            continue
        break
    if last_exc is not None:
        raise last_exc
    raise RuntimeError("Gemini 呼叫失敗，原因未知。")
