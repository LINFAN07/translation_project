import os
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

_root = Path(__file__).resolve().parent.parent
load_dotenv(_root / ".env")
load_dotenv(Path(__file__).resolve().parent / ".env")

from file_handler import read_streamlit_upload
from extract_glossary import extract_glossary
from text_splitter import split_text_with_overlap
from translator import translate_chunk, generate_summary
from docx_writer import build_translation_docx_bytes
from glossary_parse import parse_glossary_from_model
from translation_merge import join_translated_chunks
from gemini_token_estimate import (
    MODEL_OPTIONS,
    estimate_pipeline_tokens,
    usd_cost_estimate,
)
from target_languages import TARGET_LANGUAGE_OPTIONS

load_dotenv()

_USE_GEMINI_WORKER = bool((os.getenv("GEMINI_WORKER_URL") or "").strip())

st.set_page_config(
    page_title="AI 多語言翻譯助手",
    page_icon="🌐",
    layout="wide",
    initial_sidebar_state="expanded",
)

zh_ui_css = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            .stDeployButton {display: none !important;}
            div[data-testid="stFileUploader"] button[kind="secondary"] p {
                font-size: 0 !important;
            }
            div[data-testid="stFileUploader"] button[kind="secondary"] p::after {
                content: "瀏覽檔案";
                font-size: 0.875rem !important;
                font-weight: 600;
            }
            </style>
            """
st.markdown(zh_ui_css, unsafe_allow_html=True)

st.title("🌐 AI 多語言翻譯助手")
st.markdown(
    """
本工具使用 **Gemini**，可 **上傳** Word／Excel／PowerPoint／PDF／純文字，或直接 **貼上原文**。  
請在側邊欄選擇 **目標語言**，會先提取 **術語表**，再分段翻譯並參考前文摘要。側邊欄亦可使用 **count_tokens** 估算 token 量。
"""
)

if _USE_GEMINI_WORKER:
    st.success(
        "已啟用 **Cloudflare Worker** 代理：Google API 金鑰只存放在 Worker 後端，請勿在公開頁面貼金鑰。"
    )

st.info(
    "📎 **上傳方式：** 將檔案 **拖放** 到下方虛線框，或點 **「瀏覽檔案」**（介面若仍顯示 "
    "*Browse files*，意義相同）。單檔上限約 **200MB**。"
    "支援：PDF、Word（建議 .docx）、Excel（.xlsx／.xls）、PowerPoint（建議 .pptx）、.txt。"
)

# --- 側邊欄（上段）---
with st.sidebar:
    st.header("設定")
    if _USE_GEMINI_WORKER:
        st.caption(
            "翻譯與 token 估算經 **GEMINI_WORKER_URL**（與選用的 **GEMINI_WORKER_AUTH**）連線，不需填 Google 金鑰。"
        )
        api_key = ""
    else:
        api_key = st.text_input(
            "Gemini API 金鑰",
            type="password",
            value=os.getenv("GEMINI_API_KEY", ""),
            help="可向 Google AI Studio 申請。也可在 .env 設定 GEMINI_API_KEY。",
        )
        if api_key:
            os.environ["GEMINI_API_KEY"] = api_key

    model_id = st.selectbox(
        "翻譯模型",
        options=list(MODEL_OPTIONS.keys()),
        index=list(MODEL_OPTIONS.keys()).index("gemini-1.5-flash"),
        format_func=lambda k: MODEL_OPTIONS[k],
        help="實際呼叫與 count_tokens 皆使用此模型 ID。若 404 請改選其他模型。",
    )

    chunk_size = st.slider("每段字數上限（切段）", 500, 5000, 2000, step=500)
    overlap_size = st.slider("段與段重疊字數", 100, 1000, 500, step=100)

col1, col2 = st.columns(2)

with col1:
    st.subheader("原文輸入")

    uploaded = st.file_uploader(
        "選擇要上傳的檔案（可不填）",
        type=["pdf", "docx", "doc", "xlsx", "xls", "pptx", "ppt", "txt"],
        help="若同時貼上文字與上傳檔案，會 **優先使用檔案** 內容。舊版 .doc／.ppt 建議另存為 .docx／.pptx。",
    )

    input_text = st.text_area(
        "或在此貼上原文",
        height=320,
        placeholder="若未上傳檔案，請在此貼上要翻譯的全文…",
    )

    has_paste = bool(input_text and input_text.strip())
    has_upload = uploaded is not None
    can_start = (bool(api_key) or _USE_GEMINI_WORKER) and (has_paste or has_upload)

    if st.button("開始翻譯", type="primary", disabled=not can_start):
        if uploaded is not None:
            try:
                source_text = read_streamlit_upload(uploaded)
            except ValueError as e:
                st.error(str(e))
                st.stop()
            except Exception as e:
                st.error(f"讀取上傳檔失敗：{e}")
                st.stop()
            if not source_text.strip():
                st.error(
                    "無法從此檔擷取文字（可能空白或受保護）。請換格式或改貼文字。"
                )
                st.stop()
            st.caption(f"目前使用檔案：**{uploaded.name}**")
        else:
            source_text = input_text.strip()
            if not source_text:
                st.warning("請貼上文字或上傳檔案。")
                st.stop()

        progress_bar = st.progress(0)
        status_text = st.empty()

        status_text.text("正在提取術語表…")
        try:
            glossary_raw = extract_glossary(
                source_text,
                model_name=model_id,
                target_language=target_lang,
            )
            st.session_state.glossary = parse_glossary_from_model(glossary_raw)

            st.success("術語表已建立。")
            with st.expander("檢視術語表"):
                st.write(st.session_state.glossary)
        except Exception as e:
            st.error(f"提取術語表失敗：{e}")
            st.stop()

        status_text.text("正在切段…")
        chunks = split_text_with_overlap(
            source_text, chunk_size=chunk_size, overlap_size=overlap_size
        )
        num_chunks = len(chunks)
        st.info(f"全文已切成 **{num_chunks}** 段進行翻譯。")

        full_translation = []
        prev_summary = ""
        translation_incomplete = False

        for i, chunk in enumerate(chunks):
            status_text.text(f"翻譯進度：第 {i+1}／{num_chunks} 段…")
            try:
                translated_text = translate_chunk(
                    chunk,
                    st.session_state.glossary,
                    prev_summary,
                    model_name=model_id,
                )
                full_translation.append(translated_text)
                prev_summary = generate_summary(
                    translated_text, model_name=model_id
                )
                progress_bar.progress((i + 1) / num_chunks)
            except Exception as e:
                st.error(f"第 {i+1} 段翻譯失敗：{e}")
                translation_incomplete = True
                break

        st.session_state.full_translation = join_translated_chunks(
            full_translation
        )
        if translation_incomplete:
            st.warning(
                f"僅完成 {len(full_translation)}／{num_chunks} 段，下方為部分譯文。"
            )
        status_text.text("翻譯完成。")
        st.balloons()

with col2:
    st.subheader("譯文預覽")
    if "full_translation" in st.session_state:
        st.text_area(
            "譯文內容",
            value=st.session_state.full_translation,
            height=400,
            label_visibility="visible",
        )

        st.markdown("**下載譯文**")
        dl_col1, dl_col2 = st.columns(2)
        txt_data = st.session_state.full_translation
        with dl_col1:
            st.download_button(
                label="下載純文字（.txt）",
                data=txt_data.encode("utf-8"),
                file_name="譯文.txt",
                mime="text/plain; charset=utf-8",
                use_container_width=True,
            )
        with dl_col2:
            docx_bytes = build_translation_docx_bytes(
                txt_data,
                title="譯文",
                subtitle="由 AI 多語言翻譯助手產生",
            )
            st.download_button(
                label="下載 Word（.docx）",
                data=docx_bytes,
                file_name="譯文.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                use_container_width=True,
            )
        st.caption("建議另存新檔後，在 Word 再依出版需求調整排版。")
    else:
        st.info("完成翻譯後，可在此預覽並 **下載 .txt 或 .docx**。")

# --- 側邊欄（下段）：count_tokens ---
derived_source = ""
if uploaded is not None:
    try:
        derived_source = read_streamlit_upload(uploaded)
    except Exception:
        derived_source = ""
elif input_text.strip():
    derived_source = input_text.strip()

est_sig = (model_id, chunk_size, overlap_size, len(derived_source), derived_source[:4096])

with st.sidebar:
    st.divider()
    st.subheader("Token 估算（官方）")
    st.caption(
        "使用 `GenerativeModel.count_tokens`，會多次呼叫 Google API（僅計數、非生成）。"
        "輸出 token 以佔位字串估算，實際仍以帳單為準。"
    )
    if not api_key and not _USE_GEMINI_WORKER:
        st.warning("請先填寫 API 金鑰，或於部署環境設定 GEMINI_WORKER_URL。")
    elif not derived_source.strip():
        st.info("上傳檔案或貼上原文後，可在此估算。")
    else:
        if st.button("估算／更新 Token", type="secondary"):
            try:
                with st.spinner("正在呼叫 count_tokens…"):
                    est = estimate_pipeline_tokens(
                        derived_source,
                        model_id=model_id,
                        chunk_size=chunk_size,
                        overlap_size=overlap_size,
                        api_key=api_key or None,
                        target_language=target_lang,
                    )
                st.session_state["token_est"] = est
                st.session_state["token_est_sig"] = est_sig
            except Exception as e:
                st.error(f"估算失敗：{e}")

        if (
            st.session_state.get("token_est_sig") == est_sig
            and "token_est" in st.session_state
        ):
            eobj = st.session_state["token_est"]
            st.metric("切段數", eobj.num_chunks)
            st.markdown(
                f"| 項目 | Token（約） |\n|------|-------------|\n"
                f"| 術語表（輸入） | {eobj.glossary_prompt_in:,} |\n"
                f"| 術語表（輸出佔位） | {eobj.glossary_out_proxy:,} |\n"
                f"| 翻譯步驟（輸入加總） | {eobj.translate_in_total:,} |\n"
                f"| 摘要步驟（輸入加總） | {eobj.summary_in_total:,} |\n"
                f"| 翻譯步驟（輸出佔位加總） | {eobj.translate_out_proxy_total:,} |\n"
                f"| 摘要步驟（輸出佔位加總） | {eobj.summary_out_proxy_total:,} |\n"
                f"| **輸入合計** | **{eobj.input_tokens_total:,}** |\n"
                f"| **輸出合計（佔位）** | **{eobj.output_tokens_total:,}** |\n"
            )
            usd = usd_cost_estimate(
                model_id, eobj.input_tokens_total, eobj.output_tokens_total
            )
            st.caption(
                f"參考費用（USD，表內單價可依 `gemini_token_estimate.py` 調整）：約 **${usd:.4f}**"
            )

st.markdown("---")
st.caption("技術支援：Gemini · Streamlit · count_tokens")
