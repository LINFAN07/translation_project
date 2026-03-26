# 長文本翻譯專案 (LLM Translation Project)

此專案利用 **Gemini** 處理長文本翻譯，以術語表、分段重疊與滾動摘要維持一致性。

## 純前端雲端版（多人用你的網址，金鑰不給站長）

目錄 **`web/public/`** 為**純靜態**頁面：使用者的 **Gemini API 金鑰**只存在自家瀏覽器（`localStorage` 可選），翻譯請求由**瀏覽器直接呼叫 Google** `generativelanguage.googleapis.com`，**不經**專案擁有者的 Python／Worker，站長**無法**從後端讀取他人金鑰與原文。

- 本機預覽：用本機靜態伺服器開啟（勿用 `file://`，否則常無法呼叫 API），例如：  
  `npx --yes serve web/public -p 3330` → 開啟提示的 `http://localhost:3330`
- **Cloudflare Pages** 部署：在 `web` 目錄執行（首次需登入 Cloudflare：`npx wrangler login`；專案名可自改）：

```bash
cd web
npm install
npx wrangler pages deploy public --project-name=translation-gemini-client
```

部署後請至 [Google AI Studio](https://aistudio.google.com/) 或 Cloud Console **憑證**，將 API 金鑰的「HTTP 參照網址」設為你的 Pages 網域，例如 **`https://translation-gemini-client.pages.dev/*`**（與實際專案名一致），否則瀏覽器可能被 CORS／金鑰限制擋下。

本倉庫已建立的 Pages 專案預設網址：**https://translation-gemini-client.pages.dev**（每次 `wrangler pages deploy` 可能另產生預覽子網域，正式網域以前者為準）。

> 信任說明：使用者仍信任「你提供的靜態 `app.js`」未被竄改；若需最高保證請自行 clone 建置並自行部署，或比對 Git 內容。

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

**補充：瀏覽器沒自己跳出時**  
`gh` 用的是「裝置登入」：終端機會顯示**一次性代碼**，你需要**手動**開啟 [https://github.com/login/device](https://github.com/login/device)，把代碼貼上後按授權（通常**不會**自動彈出視窗）。Windows 可改用腳本先幫你開分頁再登入。**若出現「已停用指令碼執行」**，請用 `.cmd`（不依賴 PowerShell 執行原則）：

```cmd
scripts\github-device-login.cmd
```

或非指令碼、直接在專案根目錄：

```powershell
gh auth login -h github.com -p https -w
```

（畫面上會出現 `First copy your one-time code: XXXX-XXXX`，請貼到已開啟的 [device 頁面](https://github.com/login/device)。）

若堅持用 `.ps1`，請先允許本機腳本：**以系統管理員執行可省略**，一般使用者可用：

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
.\scripts\github-device-login.ps1
```

2. 在專案根目錄執行內建腳本（預設倉庫名 `translation_project`，公開）：

```cmd
scripts\github-gh-push.cmd
```

或：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\github-gh-push.ps1
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

**Cloudflare Workers** 可架設輕量後端；**Google API 金鑰只存在 Worker 的 Secrets**，不會進前端或 Git。Streamlit 無法跑在 Workers 裡，請把 **Streamlit** 仍放在 [Streamlit Cloud](https://streamlit.io/cloud)／Render／本機，只把 **Gemini 呼叫**改走 Worker。

### 本機已部署的 Worker（範例）

目前專案中已透過 Wrangler 部署一個 Worker（名稱 `translation-gemini-proxy`）。你的網址形如：

`https://translation-gemini-proxy.<你的子網域>.workers.dev`

請到 [Cloudflare Dashboard → Workers](https://dash.cloudflare.com/) 確認實際網址，並在 `.env` 或 `.streamlit/secrets.toml` 設定（**不要** commit）：

- `GEMINI_WORKER_URL`＝上述 Worker 根網址（**無結尾斜線**）
- `GEMINI_WORKER_AUTH`＝與 Worker Secret **`WORKER_AUTH_SECRET`** 相同的字串（請自行保管；若忘記，可在 `cloudflare/gemini-proxy` 目錄重新執行 `npx wrangler secret put WORKER_AUTH_SECRET` 設定新值並同步更新客戶端）

### 將 Google 金鑰寫入 Cloudflare（勿提交到 Git）

1. 在專案根目錄 `.env` 設定**真的** `GEMINI_API_KEY`（勿用佔位字）。
2. 執行（會把金鑰上傳到 Cloudflare，**不會**印出金鑰）：

```cmd
scripts\cloudflare-put-gemini-key.cmd
```

或：`powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\cloudflare-put-gemini-key.ps1`

### 重新部署或首次部署

```bash
cd cloudflare/gemini-proxy
npm install
npx wrangler login
npx wrangler secret put GEMINI_API_KEY
npx wrangler secret put WORKER_AUTH_SECRET
npx wrangler deploy
```

（本專案 Worker **已啟用** `WORKER_AUTH_SECRET` 時，未帶 `Authorization: Bearer <密碼>` 的請求會收到 `401`，可避免 Worker URL 遭他人濫用。）

設定完成後，Python 若偵測到 `GEMINI_WORKER_URL` 會**優先經 Worker**呼叫 Gemini，瀏覽器與 Git 皆**不需要**出現 Google API key。本機除錯若要改回直連，請暫時移除或清空 `GEMINI_WORKER_URL`。

Worker 端點：`POST /generate`（body: `{"model","prompt"}`）、`POST /count-tokens`（body: `{"model","text"}`）。

## 命令列（終端機）

在專案**根目錄**執行（`sys.path` 會自動對應 `src/`）：

```bash
python src/main.py path\to\file.pdf -o output_translated.txt
```

- 第一個參數為輸入檔（可為 `input.txt`、PDF、Word、Excel、PowerPoint 等）；若省略，預設 `input.txt`。
- `-o`／`--output`：輸出路徑；副檔名 `.docx` 時輸出 Word。
- `-c`／`--chunk_size`、`-v`／`--overlap`、`--model`、`--target-lang`（`zh-TW`／`ja`／`en`／`ko`）、`--save-glossary`：見 `python src/main.py -h`。

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
- `web/public/`：純前端翻譯頁（金鑰僅在瀏覽器，直連 Google）。
- `src/main.py`：CLI 入口。
- `src/app.py`：Streamlit 入口。

## 舊版說明

若僅有純文字，仍可將全文放於 `input.txt`，在根目錄執行 `python src/main.py`（等同預設輸入 `input.txt`）。
