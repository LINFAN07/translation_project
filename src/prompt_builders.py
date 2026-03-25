"""
與實際 API 呼叫一致的提示詞字串（供翻譯與 count_tokens 估算共用）。
"""

from __future__ import annotations

import json

GLOSSARY_SOURCE_CHAR_LIMIT = 10000


def _stratified_snippet(text: str, limit: int) -> str:
    """長文時擷取頭／中／尾片段，使術語表覆蓋較平均（總長仍不超過 limit）。"""
    t = text.strip()
    if len(t) <= limit:
        return t
    third = max(1, limit // 3)
    head = t[:third]
    mid_i = max(0, len(t) // 2 - third // 2)
    mid = t[mid_i : mid_i + third]
    tail = t[-third:]
    return (
        f"{head}\n\n[… 文中省略 …]\n\n{mid}\n\n[… 文中省略 …]\n\n{tail}"
    )


def _glossary_to_prompt_string(glossary: object) -> str:
    if isinstance(glossary, str):
        return glossary
    try:
        return json.dumps(glossary, ensure_ascii=False, indent=2)
    except (TypeError, ValueError):
        return str(glossary)


def build_extract_glossary_prompt(text: str) -> str:
    snippet = _stratified_snippet(text, GLOSSARY_SOURCE_CHAR_LIMIT)
    return f"""
    你是一位專業的術語提取專家。請從以下文本中提取出 20-30 個關鍵術語（包含專有名詞、技術術語、高頻關鍵字）。
    請為每個術語提供建議的繁體中文譯名。
    
    輸出格式請嚴格遵守 JSON 格式：
    {{
        "glossary": [
            {{"original": "term1", "translation": "譯名1"}},
            {{"original": "term2", "translation": "譯名2"}}
        ]
    }}
    
    文本內容：
    {snippet}  # 長文為頭／中／尾合併摘錄，總長以 {GLOSSARY_SOURCE_CHAR_LIMIT} 字為上限
    """


def build_translate_prompt(
    chunk: str, glossary: object, prev_summary: str = ""
) -> str:
    gtxt = _glossary_to_prompt_string(glossary)
    return f"""
    你是一位專業的翻譯專家，擅長將文本翻譯為流暢且優雅的繁體中文。
    
    請遵守以下規範：
    1. 參考術語表進行翻譯：{gtxt}
    2. 參考前文摘要以維持脈絡連貫性：{prev_summary}
    3. 翻譯風格應自然流暢，避免翻譯腔。
    
    待翻譯文本：
    {chunk}
    
    請直接輸出翻譯結果。
    """


def build_summary_prompt(chunk_translation: str) -> str:
    return (
        "請為以下譯文生成一段 100 字以內的簡短摘要，重點說明主要內容與脈絡：\n\n"
        f"{chunk_translation}"
    )
