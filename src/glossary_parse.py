"""
從模型輸出解析術語表 JSON；失敗時回傳原始字串供翻譯階段使用。
"""
from __future__ import annotations

import json
import re


def parse_glossary_from_model(raw: str) -> str | dict | list:
    """
    若可解析為 JSON 物件／陣列則回傳；否則回傳去_fence 後的字串或原文。
    """
    if not raw or not str(raw).strip():
        return raw
    s = str(raw).strip()
    if s.startswith("```"):
        s = re.sub(r"^```(?:json)?\s*", "", s, flags=re.IGNORECASE)
        s = re.sub(r"\s*```\s*$", "", s)
    s = s.strip()
    start = s.find("{")
    end = s.rfind("}")
    if start != -1 and end > start:
        candidate = s[start : end + 1]
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass
    start_a = s.find("[")
    end_a = s.rfind("]")
    if start_a != -1 and end_a > start_a:
        candidate = s[start_a : end_a + 1]
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass
    return s
