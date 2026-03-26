from dotenv import load_dotenv

from gemini_helpers import generate_text
from prompt_builders import build_extract_glossary_prompt
from target_languages import DEFAULT_TARGET_LANGUAGE

load_dotenv()

DEFAULT_GEMINI_MODEL = "gemini-1.5-flash"


def extract_glossary(
    text: str,
    model_name: str | None = None,
    *,
    target_language: str = DEFAULT_TARGET_LANGUAGE,
):
    """
    從文本中提取關鍵術語與建議譯名（譯名語言由 target_language 決定）
    """
    mid = model_name or DEFAULT_GEMINI_MODEL
    prompt = build_extract_glossary_prompt(text, target_lang=target_language)
    return generate_text(mid, prompt)
