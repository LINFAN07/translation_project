@echo off
chcp 65001 >nul
cd /d "%~dp0.."

gh auth status >nul 2>&1
if %errorlevel% neq 0 (
  echo Not logged in. Run first: scripts\github-device-login.cmd
  pause
  exit /b 1
)

git remote get-url origin >nul 2>&1
if %errorlevel% equ 0 (
  echo Remote "origin" already exists. To recreate: git remote remove origin
  pause
  exit /b 1
)

echo Creating public repo "translation_project" and pushing main...
gh repo create translation_project --public --source=. --remote=origin --push
if %errorlevel% neq 0 (
  pause
  exit /b 1
)
echo Done. Run: gh repo view --web
pause
