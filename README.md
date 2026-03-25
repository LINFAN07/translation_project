# 長文本翻譯專案 (LLM Translation Project)

此專案利用 **Gemini** 處理長文本翻譯，以術語表、分段重疊與滾動摘要維持一致性。

## 環境與依賴

1. Python 3.10+ 建議。
2. 在專案根目錄建立虛擬環境並安裝依賴：

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

3. 複製 `.env.example` 為 `.env`，本機開發可填 `GEMINI_API_KEY`；**上線請改走 Cloudflare Worker**（見下），勿將 `.env` 提交至 Git。

## GitHub 版本管理

### 本專案目前狀態（從中斷處接續）

若本機**已**完成 `git init` 與首次 `commit`（例如已在 `main` 分支），只需連上遠端並推送：

1. 到 GitHub 建立**空**儲存庫（不要勾選加入 README）。
2. 在專案根目錄執行（將 URL 改成你的倉庫）：

```bash
git remote add origin https://github.com/<你的帳號>/<儲存庫名稱>.git
git push -u origin main
```

若已存在 `origin`，可改用：

```bash
git remote set-url origin https://github.com/<你的帳號>/<儲存庫名稱>.git
git push -u origin main
```

推送前請確認：`git status` 乾淨，且 `git check-ignore -v .env` 顯示 `.env` 被忽略。

### 可選：GitHub CLI 建倉並推送（方式 B）

1. 安裝並**登入**（需在瀏覽器完成授權，無法由他人代登）：

```bash
winget install GitHub.cli
gh auth login -h github.com -p https -w
```

2. 在專案根目錄執行內建腳本（預設倉庫名 `translation_project`，公開）：

```powershell
.\scripts\github-gh-push.ps1
```

自訂名稱或私人倉庫：

```powershell
.\scripts\github-gh-push.ps1 -RepoName "my-translation-app"
.\scripts\github-gh-push.ps1 -RepoName "my-app" -Visibility private
```

等同手動：

```bash
cd <專案根目錄>
gh repo create <儲存庫名稱> --public --source=. --remote=origin --push
```

### 从零建立 Git 時

```bash
git init
git add .
git status   # 不應出現 .env
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/<你的帳號>/<儲存庫名稱>.git
git push -u origin main
```

## Cloudflare Worker（後端代理、隱藏 Gemini 金鑰）

**Cloudflare Workers** 可架設輕量後端；**Google API 金鑰只存在 Worker 的 Secrets**，不會進前端或 Git。Streamlit 網頁無法直接託管在 Workers 上，請將 **Streamlit** 放在 [Streamlit Community Cloud](https://streamlit.io/cloud)、Render、自有主機等，並在該環境設定 `GEMINI_WORKER_URL`（及選用的 `GEMINI_WORKER_AUTH`）。

部署 Worker：

```bash
cd cloudflare/gemini-proxy
npm install
npx wrangler login
npx wrangler secret put GEMINI_API_KEY
# 選用（強烈建議）：與本機 / Streamlit secrets 的 GEMINI_WORKER_AUTH 設成同一長隨機字串
npx wrangler secret put WORKER_AUTH_SECRET
npx wrangler deploy
```

部署完成後記下 Worker URL（例如 `https://translation-gemini-proxy.<子網域>.workers.dev`），在執行翻譯的環境設定：

- `GEMINI_WORKER_URL`：上述 URL（**不要**結尾斜線）
- `GEMINI_WORKER_AUTH`：若 Worker 已設定 `WORKER_AUTH_SECRET`，此處填**相同值**（Streamlit 請寫在 `.streamlit/secrets.toml` 或主機環境變數，勿寫進程式碼）

設定後，Python 會自動經 Worker 呼叫 Gemini，**不需**再設定 `GEMINI_API_KEY`（本機除錯仍可只用金鑰：unset `GEMINI_WORKER_URL` 即可）。

Worker 端點：`POST /generate`（body: `{"model","prompt"}`）、`POST /count-tokens`（body: `{"model","text"}`）。

## 命令列（終端機）

在專案**根目錄**執行（`sys.path` 會自動對應 `src/`）：

```bash
python src/main.py path\to\file.pdf -o output_translated.txt
```

- 第一個參數為輸入檔（可為 `input.txt`、PDF、Word、Excel、PowerPoint 等）；若省略，預設 `input.txt`。
- `-o`／`--output`：輸出路徑；副檔名 `.docx` 時輸出 Word。
- `-c`／`--chunk_size`、`-v`／`--overlap`、`--model`、`--save-glossary`：見 `python src/main.py -h`。

若某段翻譯失敗，已完成的段落仍會寫入輸出檔，程式以**結束碼 1** 結束，並於主控台標示「部分譯文」。

## Streamlit 網頁介面

請在 **`src` 目錄**下啟動（模組匯入路徑為 `file_handler` 等）：

```bash
cd src
streamlit run app.py
```

瀏覽器開啟後：若已設定 `GEMINI_WORKER_URL`，側邊欄**不需** Google 金鑰；否則請在側邊欄貼上金鑰或使用 `.env`。上傳檔案或貼上全文即可翻譯。

## 核心功能

- **術語提取：** 長文以頭／中／尾摘錄送請模型提取，兼顧前後文術語。
- **分段重疊：** 切段時優先於換行與中英句讀處切開；譯文合併時會嘗試去除重疊造成的重複接縫。
- **滾動摘要：** 每段譯後產生摘要，供下一段參考。
- **API 重試：** 可重試之錯誤或空回應時自動退避重試。

## 目錄結構（節選）

- `src/extract_glossary.py`：術語提取。
- `src/text_splitter.py`：文本切分與重疊。
- `src/translator.py`：翻譯與摘要呼叫。
- `src/gemini_helpers.py`：金鑰設定、重試、回應擷取（可改走 Worker）。
- `src/gemini_worker_client.py`：呼叫 Cloudflare Worker 代理。
- `cloudflare/gemini-proxy/`：Worker 原始碼（Gemini 金鑰僅在 Cloudflare Secrets）。
- `src/main.py`：CLI 入口。
- `src/app.py`：Streamlit 入口。

## 舊版說明

若僅有純文字，仍可將全文放於 `input.txt`，在根目錄執行 `python src/main.py`（等同預設輸入 `input.txt`）。
