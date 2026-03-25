@echo off
chcp 65001 >nul
cd /d "%~dp0.."
echo Opening https://github.com/login/device in your browser...
start "" "https://github.com/login/device"
timeout /t 2 /nobreak >nul
echo.
echo Copy the ONE-TIME CODE shown below into the GitHub page, then click Continue / Authorize.
echo.
gh auth login -h github.com -p https -w
if %ERRORLEVEL% EQU 0 (
  echo.
  echo Login OK. Next run: scripts\github-gh-push.cmd
)
pause
