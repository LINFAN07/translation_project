from dotenv import load_dotenv

from gemini_helpers import generate_text
from prompt_builders import build_summary_prompt, build_translate_prompt
from target_languages import DEFAULT_TARGET_LANGUAGE

load_dotenv()

DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"


def translate_chunk(
    chunk,
    glossary,
    prev_summary="",
    model_name: str | None = None,
    *,
    target_language: str = DEFAULT_TARGET_LANGUAGE,
):
    """
    翻譯單個段落，並參考術語表與前文摘要
    """
    mid = model_name or DEFAULT_GEMINI_MODEL
    prompt = build_translate_prompt(
        chunk, glossary, prev_summary, target_lang=target_language
    )
    return generate_text(mid, prompt)


def generate_summary(
    chunk_translation,
    model_name: str | None = None,
    *,
    target_language: str = DEFAULT_TARGET_LANGUAGE,
):
    """
    為當前翻譯段落生成摘要，供下一段參考
    """
    mid = model_name or DEFAULT_GEMINI_MODEL
    prompt = build_summary_prompt(chunk_translation, target_lang=target_language)
    return generate_text(mid, prompt)
