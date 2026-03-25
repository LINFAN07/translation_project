# GitHub CLI: create remote repo and push (method B).
# Prerequisite: gh installed, run once: gh auth login -h github.com -p https -w
# Usage from repo root:
#   .\scripts\github-gh-push.ps1
#   .\scripts\github-gh-push.ps1 -RepoName "my-translation-app"

param(
    [string]$RepoName = "translation_project",
    [ValidateSet("public", "private")]
    [string]$Visibility = "public"
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path $PSScriptRoot -Parent
Set-Location $projectRoot

if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
    Write-Host "gh not found. Install: winget install GitHub.cli" -ForegroundColor Red
    exit 1
}

cmd /c "gh auth status >nul 2>&1"
if ($LASTEXITCODE -ne 0) {
    Write-Host "Not logged in. Run this first in a terminal:" -ForegroundColor Yellow
    Write-Host "  gh auth login -h github.com -p https -w" -ForegroundColor Cyan
    Write-Host "Then run this script again." -ForegroundColor Yellow
    exit 1
}

$hasOrigin = git remote get-url origin 2>$null
if ($LASTEXITCODE -eq 0) {
    Write-Host "Remote origin already exists: $hasOrigin" -ForegroundColor Yellow
    Write-Host "To use a new repo: git remote remove origin" -ForegroundColor Yellow
    exit 1
}

Write-Host "Creating GitHub repo: $RepoName ($Visibility) and pushing main..." -ForegroundColor Green
if ($Visibility -eq "public") {
    gh repo create $RepoName --public --source=. --remote=origin --push
} else {
    gh repo create $RepoName --private --source=. --remote=origin --push
}

if ($LASTEXITCODE -eq 0) {
    Write-Host "Done. Open repo: gh repo view --web" -ForegroundColor Green
}
