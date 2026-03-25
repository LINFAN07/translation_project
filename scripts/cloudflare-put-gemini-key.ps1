# Upload GEMINI_API_KEY from repo-root .env to Cloudflare Worker secrets.
# Run from anywhere: powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\cloudflare-put-gemini-key.ps1

$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
$envFile = Join-Path $root ".env"
if (-not (Test-Path -LiteralPath $envFile)) {
    Write-Host "Missing .env at $envFile" -ForegroundColor Red
    exit 1
}
$key = $null
Get-Content -LiteralPath $envFile | ForEach-Object {
    if ($_ -match '^\s*GEMINI_API_KEY\s*=\s*(.+)\s*$') {
        $key = $matches[1].Trim().Trim('"')
    }
}
if (-not $key -or $key -eq "your_api_key_here" -or $key.Length -lt 12) {
    Write-Host "Set a real GEMINI_API_KEY in .env first (not the placeholder)." -ForegroundColor Yellow
    exit 1
}
$proxyDir = Join-Path $root "cloudflare\gemini-proxy"
Set-Location $proxyDir
$key | npx wrangler secret put GEMINI_API_KEY
if ($LASTEXITCODE -eq 0) {
    Write-Host "GEMINI_API_KEY uploaded to Worker secrets." -ForegroundColor Green
}
