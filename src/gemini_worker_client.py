"""
經由 Cloudflare Worker 呼叫 Gemini（不在本機暴露 Google API Key）。
環境變數：GEMINI_WORKER_URL（必填）、GEMINI_WORKER_AUTH（選用，對應 Worker 的 WORKER_AUTH_SECRET）。
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from typing import Any

from pathlib import Path

from dotenv import load_dotenv

_env_root = Path(__file__).resolve().parent.parent
load_dotenv(_env_root / ".env")
load_dotenv(Path(__file__).resolve().parent / ".env")


def worker_base_url() -> str:
    return (os.getenv("GEMINI_WORKER_URL") or "").strip().rstrip("/")


def _auth_headers() -> dict[str, str]:
    auth = (os.getenv("GEMINI_WORKER_AUTH") or "").strip()
    if auth:
        return {"Authorization": f"Bearer {auth}"}
    return {}


def _post_json(url: str, payload: dict[str, Any], *, timeout: int) -> dict[str, Any]:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={
            "Content-Type": "application/json; charset=utf-8",
            **_auth_headers(),
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        try:
            body = json.loads(raw)
        except json.JSONDecodeError:
            raise RuntimeError(f"Worker HTTP {e.code}: {raw[:800]}") from e
        err = body.get("error", raw)
        raise RuntimeError(f"Worker HTTP {e.code}: {err}") from e
    return json.loads(raw)


def worker_generate_text(
    model_name: str,
    prompt: str,
    *,
    timeout: int = 120,
) -> str:
    base = worker_base_url()
    if not base:
        raise ValueError("已啟用代理模式但未設定 GEMINI_WORKER_URL。")
    url = f"{base}/generate"
    body = _post_json(url, {"model": model_name, "prompt": prompt}, timeout=timeout)
    if not body.get("ok"):
        raise RuntimeError(body.get("error", "Worker 回應失敗"))
    text = body.get("text")
    if not text or not str(text).strip():
        raise RuntimeError("Worker 回應無文字。")
    return str(text).strip()


def worker_count_tokens(
    model_name: str,
    text: str,
    *,
    timeout: int = 90,
) -> int:
    base = worker_base_url()
    if not base:
        raise ValueError("已啟用代理模式但未設定 GEMINI_WORKER_URL。")
    url = f"{base}/count-tokens"
    body = _post_json(url, {"model": model_name, "text": text}, timeout=timeout)
    if not body.get("ok"):
        raise RuntimeError(body.get("error", "Worker 回應失敗"))
    n = body.get("totalTokens")
    if not isinstance(n, int):
        raise RuntimeError("Worker count-tokens 回應格式錯誤。")
    return int(n)


def worker_generate_with_retries(
    model_name: str,
    prompt: str,
    *,
    max_retries: int = 5,
    base_delay_sec: float = 1.5,
) -> str:
    last: BaseException | None = None
    for attempt in range(max_retries):
        try:
            return worker_generate_text(model_name, prompt)
        except Exception as e:
            last = e
            msg = str(e).lower()
            retry = any(
                x in msg
                for x in (
                    "429",
                    "quota",
                    "resource",
                    "503",
                    "502",
                    "504",
                    "timeout",
                    "unavailable",
                )
            )
            if not retry or attempt >= max_retries - 1:
                raise
            time.sleep(base_delay_sec * (2**attempt))
    assert last is not None
    raise last
