from dotenv import load_dotenv

from gemini_helpers import generate_text
from prompt_builders import build_extract_glossary_prompt

load_dotenv()

DEFAULT_GEMINI_MODEL = "gemini-1.5-flash"


def extract_glossary(text: str, model_name: str | None = None):
    """
    從文本中提取關鍵術語與建議譯名
    """
    mid = model_name or DEFAULT_GEMINI_MODEL
    prompt = build_extract_glossary_prompt(text)
    return generate_text(mid, prompt)
