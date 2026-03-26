import os
import sys
import argparse
from file_handler import read_file_content
from extract_glossary import extract_glossary
from text_splitter import split_text_with_overlap
from translator import translate_chunk, generate_summary
from docx_writer import save_translation_docx
from translation_merge import join_translated_chunks
from target_languages import (
    DEFAULT_TARGET_LANGUAGE,
    TARGET_LANGUAGE_OPTIONS,
    normalize_target_language,
)


def _configure_stdio_utf8() -> None:
    """避免 Windows 主控台 (cp950) 無法印出日文／中文路徑而崩潰。"""
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def main() -> int:
    """結束碼：0 成功；1 表示僅寫入部分譯文或輸入錯誤。"""
    _configure_stdio_utf8()
    # 設定命令行參數解析
    parser = argparse.ArgumentParser(
        description="AI 文本翻譯工具 (Terminal 模式 - 支援 TXT, PDF, DOCX, XLSX, XLS, PPTX)"
    )
    parser.add_argument("input", help="要翻譯的輸入檔案路徑 (例如: input.pdf, doc.docx)", nargs='?', default="input.txt")
    parser.add_argument(
        "-o",
        "--output",
        help="輸出檔案路徑；副檔名 .docx 則輸出 Word (預設: output_translated.txt)",
        default="output_translated.txt",
    )
    parser.add_argument(
        "--save-glossary",
        help="將術語表另存為文字檔（可選，便於驗證）",
        default=None,
        metavar="PATH",
    )
    parser.add_argument("-c", "--chunk_size", type=int, help="段落切分大小 (預設: 2000)", default=2000)
    parser.add_argument("-v", "--overlap", type=int, help="重疊區間大小 (預設: 500)", default=500)
    parser.add_argument(
        "--model",
        type=str,
        default="gemini-1.5-flash",
        help="Gemini 模型名稱 (預設: gemini-1.5-flash)",
    )
    parser.add_argument(
        "--target-lang",
        type=str,
        default=DEFAULT_TARGET_LANGUAGE,
        choices=list(TARGET_LANGUAGE_OPTIONS.keys()),
        metavar="CODE",
        help="譯文目標語言：zh-TW／ja／en／ko（預設: zh-TW）",
    )

    args = parser.parse_args()
    target_lang = normalize_target_language(args.target_lang)

    input_path = args.input
    output_path = args.output

    # 檢查輸入檔案是否存在
    if not os.path.exists(input_path):
        print(f"錯誤: 找不到檔案 '{input_path}'")
        print(f"用法: py src/main.py [檔案路徑]")
        return 1

    print(f"正在讀取檔案: {input_path}")
    try:
        full_text = read_file_content(input_path)
        if not full_text.strip():
            print("錯誤: 檔案內容為空或無法提取文字。")
            return 1
    except Exception as e:
        print(f"讀取檔案時發生錯誤: {e}")
        return 1

    # 1. 提取術語表
    print("-" * 30)
    print("正在提取術語表...")
    glossary = extract_glossary(
        full_text, model_name=args.model, target_language=target_lang
    )
    print("術語表提取完成。")
    if args.save_glossary:
        try:
            gdir = os.path.dirname(os.path.abspath(args.save_glossary))
            if gdir:
                os.makedirs(gdir, exist_ok=True)
            with open(args.save_glossary, "w", encoding="utf-8") as gf:
                gf.write(glossary)
            print(f"術語表已儲存: {args.save_glossary}")
        except OSError as e:
            print(f"警告: 無法寫入術語表檔案: {e}")

    # 2. 切分文本
    print("-" * 30)
    print(f"正在切分文本 (大小: {args.chunk_size}, 重疊: {args.overlap})...")
    chunks = split_text_with_overlap(full_text, chunk_size=args.chunk_size, overlap_size=args.overlap)
    print(f"文本已切分為 {len(chunks)} 個段落。")

    # 3. 循環翻譯
    print("-" * 30)
    full_translation = []
    prev_summary = ""
    translation_stopped_early = False

    for i, chunk in enumerate(chunks):
        print(f"正在翻譯第 {i+1}/{len(chunks)} 段...")
        try:
            translated_text = translate_chunk(
                chunk,
                glossary,
                prev_summary,
                model_name=args.model,
                target_language=target_lang,
            )
            full_translation.append(translated_text)

            # 更新摘要供下一段使用
            prev_summary = generate_summary(
                translated_text,
                model_name=args.model,
                target_language=target_lang,
            )
        except Exception as e:
            print(f"翻譯第 {i+1} 段時發生錯誤: {e}")
            translation_stopped_early = True
            break

    # 4. 儲存結果
    print("-" * 30)
    joined = join_translated_chunks(full_translation)
    if translation_stopped_early:
        print(
            f"警告: 僅完成 {len(full_translation)}/{len(chunks)} 段，輸出為部分譯文。"
        )
    out_ext = os.path.splitext(output_path)[1].lower()
    if out_ext == ".docx":
        title = f"譯文：{os.path.basename(input_path)}"
        subtitle = (
            "由 translation_project 管線產生（術語表 + 分段翻譯 + 前文摘要）。"
        )
        save_translation_docx(
            output_path,
            joined,
            title=title,
            subtitle=subtitle,
        )
    else:
        out_dir = os.path.dirname(os.path.abspath(output_path))
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(joined)

    if translation_stopped_early:
        print(f"已寫入目前進度至: {output_path}")
    else:
        print(f"翻譯完成！結果已儲存至: {output_path}")

    if translation_stopped_early:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
