"""
目標翻譯語言：與提示詞共用（Python Streamlit／CLI 與 token 估算一致）。
"""

from __future__ import annotations

# UI：code -> 顯示名稱
TARGET_LANGUAGE_OPTIONS: dict[str, str] = {
    "zh-TW": "繁體中文",
    "ja": "日文",
    "en": "英文",
    "ko": "韓文",
}

DEFAULT_TARGET_LANGUAGE = "zh-TW"


def normalize_target_language(code: str | None) -> str:
    if code and code in TARGET_LANGUAGE_OPTIONS:
        return code
    return DEFAULT_TARGET_LANGUAGE


def get_target_config(target_lang: str) -> dict[str, str]:
    """單一語言的提示詞片段；target_lang 請先 normalize。"""
    t = normalize_target_language(target_lang)
    return TARGET_LANGUAGE_PROMPTS[t]


# 各語言提示（術語表「translation」欄、譯文語言、摘要語言）
TARGET_LANGUAGE_PROMPTS: dict[str, dict[str, str]] = {
    "zh-TW": {
        "glossary_hint": "請為每個術語提供建議的繁體中文譯名。",
        "translate_goal": "流暢且優雅的繁體中文",
        "summary_lead": (
            "請為以下譯文生成一段 100 字以內的簡短摘要，使用繁體中文，"
            "重點說明主要內容與脈絡：\n\n"
        ),
        "summary_placeholder_prev": (
            "前文摘要（繁體中文）：本段譯文重點為情境推進與人物動機，"
            "需與下一段銜接。"
        ),
        "summary_out_sample": (
            "摘要占位：重點為情境推進與人物動機，承接上段脈絡並為下段鋪墊。"
        ),
    },
    "ja": {
        "glossary_hint": (
            "各用語について、文脈に合った自然な日本語の訳語を付けてください。"
        ),
        "translate_goal": "自然で読みやすい日本語",
        "summary_lead": (
            "以下の訳文を読み、日本語で内容と脈絡を押さえた短い要約を"
            "おおよそ 200 字以内で書いてください：\n\n"
        ),
        "summary_placeholder_prev": (
            "前文要約（日本語）：登場人物の状況と次の展開の手がかりを簡潔に示す。"
        ),
        "summary_out_sample": (
            "要約：状況の進展と人物の動機を押さえ、次の段落へつなげる内容。"
        ),
    },
    "en": {
        "glossary_hint": (
            "For each term, give a concise, natural English gloss or translation "
            "appropriate to the text."
        ),
        "translate_goal": "fluent, natural English",
        "summary_lead": (
            "Read the following translation and write a brief summary in English "
            "(about 80–120 words) capturing the main points and context:\n\n"
        ),
        "summary_placeholder_prev": (
            "Prior summary (English): Key situation, motivations, and hooks for "
            "the next segment."
        ),
        "summary_out_sample": (
            "Summary: Advances the situation and character motives; bridges to the "
            "next part."
        ),
    },
    "ko": {
        "glossary_hint": (
            "각 용어에 대해 문맥에 맞는 자연스러운 한국어 표기나 번역을 제시하세요."
        ),
        "translate_goal": "자연스럽고 읽기 쉬운 한국어",
        "summary_lead": (
            "다음 번역문을 바탕으로, 핵심 내용과 맥락을 담은 짧은 요약을 "
            "한국어로 약 200자 내외로 작성하세요：\n\n"
        ),
        "summary_placeholder_prev": (
            "이전 요약(한국어): 상황 전개와 인물 동기, 다음 단과의 연결을 간단히."
        ),
        "summary_out_sample": (
            "요약: 상황과 인물의 동기를 이어 다음 단으로 넘어가는 내용."
        ),
    },
}
