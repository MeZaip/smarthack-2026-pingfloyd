<#
  Start SafeHouse on Windows - the Windows version of ./run.sh.

    .\run.ps1                  AI gateway (if a key / Ollama is configured) + UI on http://127.0.0.1:8000
    .\run.ps1 -Demo            same, with a separate demo history pre-loaded from tests\fixtures\validation
    .\run.ps1 -NoAI            UI only; the assistant answers from the built-in, verified texts
    .\run.ps1 -Port 9000       UI on another port
    .\run.ps1 -NoBrowser       do not open the browser
    .\run.ps1 -App             the end-user app window instead (same as double-clicking SafeHouse.cmd)

  From cmd.exe use run.cmd with the same options. Ctrl+C stops everything started here.

  Why not WSL: WSL2 sits behind a NAT, so it cannot see the hotspot's devices directly (no ARP, no MACs,
  no SYN scan) even on a private network. Run SafeHouse natively on Windows. Live scans need Nmap for
  Windows (https://nmap.org/download, includes Npcap); the "Check my network" button asks for permission
  through the normal Windows dialog, so this script itself does NOT need an administrator terminal.
#>
param(
    [switch]$Demo,
    [switch]$NoAI,
    [int]$Port = 8000,
    [string]$ListenHost = "127.0.0.1",
    [switch]$NoBrowser,
    [switch]$App
)
# "Continue": Windows PowerShell 5.1 turns harmless stderr output of python/pip into terminating errors
# under "Stop"; failures are checked explicitly below instead.
$ErrorActionPreference = "Continue"
Set-Location $PSScriptRoot
$env:PYTHONUTF8 = "1"

# ---------------------------------------------------------------- python env (separate from the WSL .venv)
$Venv = ".venv-windows"
$Py = Join-Path $Venv "Scripts\python.exe"
if (-not (Test-Path $Py)) {
    Write-Host "* Creating $Venv ..."
    try { & py -3 -m venv $Venv } catch { }
    if (-not (Test-Path $Py)) { & python -m venv $Venv }
    if (-not (Test-Path $Py)) { throw "Python 3.10+ not found. Install it from https://www.python.org/downloads/ (tick 'Add to PATH')." }
}
$want = (Get-FileHash requirements.txt -Algorithm SHA256).Hash
$stamp = Join-Path $Venv "requirements.sha"
if (-not (Test-Path $stamp) -or (Get-Content $stamp -Raw).Trim() -ne $want) {
    Write-Host "* Installing requirements ..."
    & $Py -m pip install -q --disable-pip-version-check --upgrade pip
    & $Py -m pip install -q --disable-pip-version-check -r requirements.txt
    if ($LASTEXITCODE -ne 0) { throw "pip install failed" }
    Set-Content $stamp $want
}

# ---------------------------------------------------------------- settings (.env is optional, never committed)
function Get-Setting([string]$Name) {
    $v = [Environment]::GetEnvironmentVariable($Name)
    if (-not $v -and (Test-Path .env)) {
        $line = Select-String -Path .env -Pattern "^$Name=" | Select-Object -Last 1
        if ($line) { $v = $line.Line.Split("=", 2)[1].Trim().Trim('"', "'") }
    }
    return $v
}

function Test-Up([string]$Url) {
    try {   # no system proxy for localhost (Windows PowerShell 5.1 has no -NoProxy)
        $req = [System.Net.WebRequest]::Create($Url); $req.Proxy = $null; $req.Timeout = 1000
        $resp = $req.GetResponse(); $resp.Close(); return $true
    } catch { return $false }
}

function Wait-Up([string]$Url, [System.Diagnostics.Process]$Proc, [int]$Seconds = 20) {
    for ($i = 0; $i -lt ($Seconds * 3); $i++) {
        if (Test-Up $Url) { return $true }
        if ($Proc -and $Proc.HasExited) { return $false }
        Start-Sleep -Milliseconds 330
    }
    return $false
}

# ---------------------------------------------------------------- checks the user can act on
$nmap = Get-Command nmap -ErrorAction SilentlyContinue
if (-not $nmap -and -not (Test-Path "C:\Program Files (x86)\Nmap\nmap.exe") -and -not (Test-Path "C:\Program Files\Nmap\nmap.exe")) {
    Write-Host "! Nmap for Windows is not installed: the UI works, but live scans need it -> https://nmap.org/download" -ForegroundColor Yellow
}

if ($App) {
    & $Py -m netcheck app
    exit $LASTEXITCODE
}

if ($Demo) {
    $env:NETCHECK_DB = Join-Path $HOME ".netcheck\demo.sqlite"
    Write-Host "* Demo history: $($env:NETCHECK_DB) (your real history is not touched)"
    & $Py -m netcheck history delete --yes *> $null
    & $Py -m netcheck history add tests\fixtures\validation\ *> $null
}

# ---------------------------------------------------------------- services
$procs = @()
try {
    if ($NoAI) {
        Write-Host "* AI: off (-NoAI); the assistant answers from the built-in texts."
        $env:NETCHECK_LLM_PROVIDER = "none"
    } else {
        $gwPort = Get-Setting "NETCHECK_GATEWAY_PORT"; if (-not $gwPort) { $gwPort = "8787" }
        $backend = Get-Setting "NETCHECK_GATEWAY_BACKEND"; if (-not $backend) { $backend = "claude" }
        if ($backend -eq "claude" -and -not (Get-Setting "ANTHROPIC_API_KEY")) {
            Write-Host "* AI gateway: skipped (no ANTHROPIC_API_KEY in the environment or .env)."
            Write-Host "  The assistant will answer from the built-in texts. To enable AI: copy .env.example .env and set the key."
            $env:NETCHECK_LLM_PROVIDER = "none"
        } elseif (Test-Up "http://127.0.0.1:$gwPort/health") {
            Write-Host "* AI gateway already running on http://127.0.0.1:$gwPort"
            $env:NETCHECK_AI_URL = "http://127.0.0.1:$gwPort"
        } else {
            Write-Host "* AI gateway ($backend) on http://127.0.0.1:$gwPort ..."
            $gw = Start-Process -FilePath $Py -ArgumentList "-m", "gateway", "--host", "127.0.0.1", "--port", $gwPort `
                  -NoNewWindow -PassThru
            $procs += $gw
            $env:NETCHECK_AI_URL = "http://127.0.0.1:$gwPort"
            if (-not (Wait-Up "http://127.0.0.1:$gwPort/health" $gw)) {
                Write-Host "  x gateway did not start; continuing with built-in answers" -ForegroundColor Yellow
                $env:NETCHECK_LLM_PROVIDER = "none"
            }
        }
    }

    Write-Host "* Web UI + JSON API on http://${ListenHost}:$Port   (Ctrl+C to stop)"
    $ui = Start-Process -FilePath $Py -ArgumentList "-m", "netcheck", "serve", "--host", $ListenHost, "--port", $Port `
          -NoNewWindow -PassThru
    $procs += $ui
    if (Wait-Up "http://127.0.0.1:$Port/api/scans" $ui 30) {
        if (-not $NoBrowser) { Start-Process "http://127.0.0.1:$Port/" }
    } else {
        Write-Host "x The web UI did not start (is port $Port busy? try -Port 9000)" -ForegroundColor Red
    }
    Wait-Process -Id $ui.Id
}
finally {
    foreach ($p in $procs) { if ($p -and -not $p.HasExited) { Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue } }
    Write-Host "`n* Stopped."
}
