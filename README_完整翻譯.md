# 如何產生「整份 PDF／長文本」的完整譯文（供品質驗證）

先前產生的 Word 檔是**對話中的節選示範**，無法代表長文本管線品質。  
要驗證本專案真正的翻譯效果，請用 **Terminal 跑完整管線**（會依段落多次呼叫 Gemini）。

## 前置條件

1. 已設定環境變數 `GEMINI_API_KEY`（或專案根目錄有 `.env`）。
2. 已安裝依賴：`py -m pip install google-generativeai python-dotenv pymupdf python-docx`

## 一鍵：PDF → 完整繁中譯文 Word

在專案根目錄 `translation_project` 執行（路徑請用引號包住）：

```powershell
py src/main.py "你的檔案.pdf" -o "output/full_translation.docx" --save-glossary "output/glossary_raw.txt"
```

- **`-o` 以 `.docx` 結尾**：會輸出 Word（完整譯文，依雙換行分段）。
- **`--save-glossary`**（可選）：把術語表原始回應存成文字檔，方便你對照。

純文字輸出：

```powershell
py src/main.py "你的檔案.pdf" -o "output/full_translation.txt"
```

## 長文本建議參數（可選）

若單段太長導致 API 不穩，可略降 chunk、略增 overlap：

```powershell
py src/main.py "你的檔案.pdf" -o "output/full_translation.docx" -c 1500 -v 400
```

## 說明

- 翻譯會走與 `translator.py` 相同的邏輯：術語表 → 切段 → 每段參考前段摘要。
- PDF 擷取後會自動做**簡單雜訊清理**（例如移除 `-- 1 of 24 --` 這類頁面標記），減少干擾。
- **完整翻譯會消耗較多 API 次數**；若需省費用，請改用自己本機模型（例如 Ollama）或 Cursor 內手動分段，那是另一套接法。
