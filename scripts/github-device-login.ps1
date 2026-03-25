# GitHub CLI device login helper: opens the device page in your default browser,
# then runs gh auth login (you must paste the one-time code from the terminal).
# Usage: .\scripts\github-device-login.ps1

$ErrorActionPreference = "Continue"
$projectRoot = Split-Path $PSScriptRoot -Parent
Set-Location $projectRoot

if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
    Write-Host "Install GitHub CLI: winget install GitHub.cli" -ForegroundColor Red
    exit 1
}

Write-Host "Opening https://github.com/login/device in your default browser..." -ForegroundColor Green
Write-Host "If nothing opens, copy this URL into the address bar yourself." -ForegroundColor Yellow
Start-Process "https://github.com/login/device"
Start-Sleep -Seconds 2

Write-Host ""
Write-Host "Next: copy the ONE-TIME CODE from gh below into the GitHub page, then Authorize." -ForegroundColor Cyan
Write-Host ""

gh auth login -h github.com -p https -w

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "Login OK. Push with: .\scripts\github-gh-push.ps1" -ForegroundColor Green
}
