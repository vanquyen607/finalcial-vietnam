param(
    [string]$Backend = 'D:\Desktop\finan\gold\backend',
    [string]$Logs = 'D:\Desktop\finan\gold\_logs'
)

# Giu cho Aurum Terminal luon song:
#  - app (port 8000) mat        -> khoi dong lai
#  - tunnel (funnel/cloudflared) mat -> goi tunnel.ps1 mo lai
# Chay ngam, ghi log vao gold\_logs\watchdog.log

$ErrorActionPreference = 'SilentlyContinue'
$logFile = Join-Path $Logs 'watchdog.log'
$pidFile = Join-Path $Logs 'watchdog.pid'
$urlFile = Join-Path $Logs 'url.txt'
$health = 'http://127.0.0.1:8000/api/health'
$tunnelPs1 = 'D:\Desktop\finan\gold\scripts\tunnel.ps1'
$ts = 'C:\Program Files\Tailscale\tailscale.exe'

# 1 instance only
if (Test-Path -LiteralPath $pidFile) {
    $oldPid = (Get-Content -LiteralPath $pidFile -ErrorAction SilentlyContinue | Select-Object -First 1)
    if ($oldPid -and $oldPid -ne $PID) {
        $proc = Get-CimInstance Win32_Process -Filter "ProcessId = $oldPid" -ErrorAction SilentlyContinue
        if ($proc -and $proc.CommandLine -like '*watchdog.ps1*') { exit 0 }
    }
}
Set-Content -LiteralPath $pidFile -Value $PID -Encoding ascii

function Write-Log([string]$msg) {
    Add-Content -LiteralPath $logFile -Value ("{0} {1}" -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $msg)
}

Write-Log ("watchdog START pid={0}" -f $PID)

function Test-App {
    try {
        $r = Invoke-WebRequest -Uri $health -TimeoutSec 5 -UseBasicParsing
        return ($r.StatusCode -eq 200)
    } catch { return $false }
}

function Start-App {
    Remove-Item (Join-Path $Logs 'app.out.log'), (Join-Path $Logs 'app.err.log') -ErrorAction SilentlyContinue
    Start-Process -FilePath python -ArgumentList 'run.py' -WorkingDirectory $Backend -WindowStyle Minimized `
        -RedirectStandardOutput (Join-Path $Logs 'app.out.log') `
        -RedirectStandardError (Join-Path $Logs 'app.err.log')
    Write-Log 'app -> restarted'
}

function Get-Url {
    return (Get-Content -LiteralPath $urlFile -ErrorAction SilentlyContinue | Select-Object -First 1)
}

function Test-Tunnel {
    $u = Get-Url
    if (-not $u) { return $false }
    if ($u -like '*.ts.net') {
        if (-not (Get-Process -Name 'tailscaled' -ErrorAction SilentlyContinue)) { return $false }
        $fs = & $ts funnel status 2>&1 | Out-String
        return ($fs -match '127\.0\.0\.1:8000')
    }
    if ($u -like '*.trycloudflare.com') { return [bool](Get-Process -Name 'cloudflared' -ErrorAction SilentlyContinue) }
    return $false
}

function Start-Tunnel {
    Write-Log 'tunnel -> restarting via tunnel.ps1'
    $old = Get-Url
    & powershell -NoProfile -ExecutionPolicy Bypass -File $tunnelPs1 -Logs $Logs -TimeoutSec 60 | Out-Null
    $new = Get-Url
    if ($new) { Write-Log ("tunnel -> OK: {0}" -f $new) }
    else { Write-Log 'tunnel -> FAILED (van chua co link)' }
    if ($old -and $new -and $old -ne $new) {
        Write-Log ("LINK DOI: {0}  =>  {1}" -f $old, $new)
    }
}

while ($true) {
    if (-not (Test-App)) { Write-Log 'app -> down'; Start-App; Start-Sleep -Seconds 8 }
    if (-not (Test-Tunnel)) { Write-Log 'tunnel -> down'; Start-Tunnel; Start-Sleep -Seconds 5 }
    Start-Sleep -Seconds 15
}
