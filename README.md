# 長文本翻譯（瀏覽器端金鑰）

本倉庫僅保留 **純靜態前端**：`web/public/`。使用者的 **Gemini API 金鑰**只存在自家瀏覽器（`localStorage`，鍵名 `translation_project_gemini_key_v1`），翻譯請求由瀏覽器直接呼叫 Google `generativelanguage.googleapis.com`，**不經**專案擁有者的後端。

## 本機預覽

勿用 `file://` 開啟（常無法呼叫 API）。例如：

```bash
npx --yes serve web/public -p 3330
```

再開啟瀏覽器提示的 `http://localhost:3330`。

## Cloudflare Pages 部署

在 `web` 目錄執行（首次需登入：`npx wrangler login`；專案名可自改）：

```bash
cd web
npm install
npx wrangler pages deploy public --project-name=translation-gemini-client
```

部署後請至 [Google AI Studio](https://aistudio.google.com/) 或 Cloud Console **憑證**，將 API 金鑰的「HTTP 參照網址」設為你的 Pages 網域，例如 **`https://translation-gemini-client.pages.dev/*`**（與實際專案名一致），否則瀏覽器可能被 CORS／金鑰限制擋下。

本倉庫已建立的 Pages 預設網址：**https://translation-gemini-client.pages.dev**（每次部署可能另產生預覽網址，正式網域以前者為準）。

> 信任說明：使用者仍信任「你提供的靜態 `app.js`」未被竄改；若需最高保證請自行 clone 建置並自行部署，或比對 Git 內容。

## 環境變數

純前端**不需要** `.env` 即可跑；若需本地備份範本可參考 `.env.example`（可留空）。

## GitHub 版本管理

### 已有 `main` 時只連遠端並推送

1. 在 GitHub 建立**空**儲存庫（不要勾選加入 README）。
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

推送前請確認：`git status` 乾淨，且 `git check-ignore -v .env` 顯示 `.env` 被忽略（若你有本機 `.env`）。

### 可選：GitHub CLI 建倉並推送

1. 安裝並**登入**（需在瀏覽器完成授權）：

```bash
winget install GitHub.cli
gh auth login -h github.com -p https -w
```

**補充：瀏覽器沒自己跳出時**  
`gh` 使用「裝置登入」：終端機會顯示**一次性代碼**，請手動開啟 [https://github.com/login/device](https://github.com/login/device)，把代碼貼上後按授權。Windows 可改用腳本：

```cmd
scripts\github-device-login.cmd
```

或非指令碼：

```powershell
gh auth login -h github.com -p https -w
```

若堅持用 `.ps1`，請先允許本機腳本：

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

## 目錄結構

- `web/public/`：靜態頁（`index.html`、`app.js`、`styles.css`）。
- `web/package.json`：僅 `wrangler` 用於 Pages 部署。
- `scripts/`：可選的 GitHub CLI 輔助腳本。

## 本機若仍見 `cloudflare/gemini-proxy` 資料夾

舊版 Worker 專案已自倉庫移除。若 Windows 顯示「資料夾使用中」無法刪除，請關閉以該路徑為工作目錄的終端機／編輯器後再刪除，或暫停 OneDrive 同步後重試。
