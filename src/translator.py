from dotenv import load_dotenv

from gemini_helpers import generate_text
from prompt_builders import build_summary_prompt, build_translate_prompt

load_dotenv()

DEFAULT_GEMINI_MODEL = "gemini-1.5-flash"


def translate_chunk(
    chunk, glossary, prev_summary="", model_name: str | None = None
):
    """
    翻譯單個段落，並參考術語表與前文摘要
    """
    mid = model_name or DEFAULT_GEMINI_MODEL
    prompt = build_translate_prompt(chunk, glossary, prev_summary)
    return generate_text(mid, prompt)


def generate_summary(chunk_translation, model_name: str | None = None):
    """
    為當前翻譯段落生成摘要，供下一段參考
    """
    mid = model_name or DEFAULT_GEMINI_MODEL
    prompt = build_summary_prompt(chunk_translation)
    return generate_text(mid, prompt)
