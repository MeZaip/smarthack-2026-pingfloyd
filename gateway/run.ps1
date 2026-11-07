# Start the netcheck AI gateway on Windows (team machine only).
#   powershell -ExecutionPolicy Bypass -File gateway\run.ps1
# The API key is read from .env in the project root (ANTHROPIC_API_KEY=...), which git ignores.
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

if (-not (Test-Path ".env") -and -not $env:ANTHROPIC_API_KEY) {
    Write-Host "No .env found. Copy .env.example to .env and put your key in ANTHROPIC_API_KEY=" -ForegroundColor Yellow
    exit 1
}

$env:PYTHONUTF8 = "1"
python -m gateway
