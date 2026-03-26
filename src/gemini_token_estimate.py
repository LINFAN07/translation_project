"""
使用 Google 官方 GenerativeModel.count_tokens（tokenizer API）估算本專案管線 token 量。

說明：
- 輸出 token 在未實際生成前無法百分之百確定，故以「與輸出同語種／相近長度」的佔位字串送 count_tokens，僅供事前參考。
- 實際計費以 Google 帳單為準；下方 USD 單價為可修改之參考表。
"""
from __future__ import annotations

import os
from dataclasses import dataclass

import google.generativeai as genai

from gemini_helpers import ensure_genai_configured
from gemini_worker_client import worker_base_url, worker_count_tokens
from prompt_builders import (
    build_extract_glossary_prompt,
    build_summary_prompt,
    build_translate_prompt,
)
from target_languages import get_target_config, normalize_target_language
from text_splitter import split_text_with_overlap

# 模型 ID 與顯示名稱（依 https://ai.google.dev/gemini-api/docs/models 更新；勿使用已對新用戶關閉的 2.0 系列）
MODEL_OPTIONS: dict[str, str] = {
    "gemini-2.5-flash": "Gemini 2.5 Flash（建議）",
    "gemini-2.5-pro": "Gemini 2.5 Pro",
    "gemini-1.5-flash": "Gemini 1.5 Flash",
    "gemini-1.5-pro": "Gemini 1.5 Pro",
}

# 參考：美元／每百萬 tokens（請定期對照 https://ai.google.dev/pricing 更新）
USD_PER_1M_TOKENS: dict[str, dict[str, float]] = {
    "gemini-2.5-flash": {"input": 0.15, "output": 0.60},
    "gemini-2.5-pro": {"input": 1.25, "output": 10.00},
    "gemini-1.5-flash": {"input": 0.075, "output": 0.30},
    "gemini-1.5-pro": {"input": 1.25, "output": 5.00},
}

# 術語表 API 回傳之輸出佔位（JSON 風格，長度與結構接近常見回應）
_GLOSSARY_OUTPUT_SAMPLE = """```json
{
  "glossary": [
    {"original": "terma", "translation": "術語甲"},
    {"original": "termb", "translation": "術語乙"},
    {"original": "termc", "translation": "術語丙"},
    {"original": "termd", "translation": "術語丁"},
    {"original": "terme", "translation": "術語戊"},
    {"original": "termf", "translation": "術語己"},
    {"original": "termg", "translation": "術語庚"},
    {"original": "termh", "translation": "術語辛"},
    {"original": "termi", "translation": "術語壬"},
    {"original": "termj", "translation": "術語癸"}
  ]
}
```"""

# 摘要步驟的「譯文」輸入佔位：以當段原文長度代理譯文 token 量級（中日對譯長度常相近）
def _translation_output_proxy(chunk: str) -> str:
    return chunk


def _glossary_proxy_from_source(source_text: str) -> str:
    """
    術語表實際字串在提取前未知。以原文前段擷取作為長度／語種密度近似佔位。
    """
    if not source_text:
        return ""
    n = min(4000, max(120, len(source_text) // 5))
    return source_text[:n]


@dataclass
class PipelineTokenEstimate:
    model_id: str
    num_chunks: int
    glossary_prompt_in: int
    glossary_out_proxy: int
    translate_in_total: int
    summary_in_total: int
    translate_out_proxy_total: int
    summary_out_proxy_total: int

    @property
    def input_tokens_total(self) -> int:
        return (
            self.glossary_prompt_in
            + self.translate_in_total
            + self.summary_in_total
        )

    @property
    def output_tokens_total(self) -> int:
        return (
            self.glossary_out_proxy
            + self.translate_out_proxy_total
            + self.summary_out_proxy_total
        )


def estimate_pipeline_tokens(
    source_text: str,
    *,
    model_id: str,
    chunk_size: int,
    overlap_size: int,
    api_key: str | None = None,
    target_language: str = "zh-TW",
) -> PipelineTokenEstimate:
    if not source_text or not source_text.strip():
        raise ValueError("原文為空，無法估算。")

    tl = normalize_target_language(target_language)
    tcfg = get_target_config(tl)

    use_worker = bool(worker_base_url())
    model = None
    if use_worker:
        pass
    else:
        key = api_key or os.getenv("GEMINI_API_KEY")
        if not key:
            raise ValueError(
                "需要 GEMINI_API_KEY，或設定 GEMINI_WORKER_URL 改由 Cloudflare 代理 count_tokens。"
            )
        ensure_genai_configured(key)
        model = genai.GenerativeModel(model_id)

    def count_tokens_text(text: str) -> int:
        t = text if isinstance(text, str) else str(text)
        if use_worker:
            return worker_count_tokens(model_id, t)
        assert model is not None
        return int(model.count_tokens(t).total_tokens)

    chunks = split_text_with_overlap(
        source_text, chunk_size=chunk_size, overlap_size=overlap_size
    )
    num_chunks = len(chunks)
    glossary_proxy = _glossary_proxy_from_source(source_text)

    glossary_prompt = build_extract_glossary_prompt(source_text, target_lang=tl)
    glossary_prompt_in = count_tokens_text(glossary_prompt)
    glossary_out_proxy = count_tokens_text(_GLOSSARY_OUTPUT_SAMPLE)

    translate_in_total = 0
    summary_in_total = 0
    translate_out_proxy_total = 0
    summary_out_proxy_total = 0

    for i, chunk in enumerate(chunks):
        prev = "" if i == 0 else tcfg["summary_placeholder_prev"]
        t_in = build_translate_prompt(chunk, glossary_proxy, prev, target_lang=tl)
        translate_in_total += count_tokens_text(t_in)

        trans_proxy = _translation_output_proxy(chunk)
        translate_out_proxy_total += count_tokens_text(trans_proxy)

        s_in = build_summary_prompt(trans_proxy, target_lang=tl)
        summary_in_total += count_tokens_text(s_in)

        summary_out_sample = tcfg["summary_out_sample"]
        summary_out_proxy_total += count_tokens_text(summary_out_sample)

    return PipelineTokenEstimate(
        model_id=model_id,
        num_chunks=num_chunks,
        glossary_prompt_in=glossary_prompt_in,
        glossary_out_proxy=glossary_out_proxy,
        translate_in_total=translate_in_total,
        summary_in_total=summary_in_total,
        translate_out_proxy_total=translate_out_proxy_total,
        summary_out_proxy_total=summary_out_proxy_total,
    )


def usd_cost_estimate(model_id: str, input_tokens: int, output_tokens: int) -> float:
    rates = USD_PER_1M_TOKENS.get(model_id)
    if not rates:
        return 0.0
    return (
        (input_tokens / 1_000_000) * rates["input"]
        + (output_tokens / 1_000_000) * rates["output"]
    )
