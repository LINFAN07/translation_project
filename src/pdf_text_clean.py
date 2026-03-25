"""
PDF 擷取文字常見雜訊清理（提升長文本翻譯一致性）。
"""
import re


def clean_pdf_extracted_text(text: str) -> str:
    if not text:
        return text
    # 例如: -- 1 of 24 --
    text = re.sub(r"--\s*\d+\s+of\s+\d+\s*--", "", text, flags=re.IGNORECASE)
    # 多餘空白行收斂
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
