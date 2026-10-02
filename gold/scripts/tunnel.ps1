param(
    [string]$Logs = 'D:\Desktop\finan\gold\_logs',
    [int]$TimeoutSec = 60
)

# Tao/con lai duong cong khai.
#   +uu tien: Tailscale Funnel  -> link CO DINH (https://<may>.<tailnet>.ts.net)
#   +fallback: cloudflared quick tunnel -> link doi moi lan mo lai
# Ket qua: url.txt (bat doc), tunnel.hint.txt (can user lam gi do, neu co).
$ErrorActionPreference = 'SilentlyContinue'
$urlFile = Join-Path $Logs 'url.txt'
$hintFile = Join-Path $Logs 'tunnel.hint.txt'
$ts = 'C:\Program Files\Tailscale\tailscale.exe'

Remove-Item -LiteralPath $hintFile -ErrorAction SilentlyContinue

function Save-Url([string]$u) {
    Set-Content -LiteralPath $urlFile -Value $u -NoNewline -Encoding ascii
}
function Set-Hint([string]$m) {
    Set-Content -LiteralPath $hintFile -Value $m -Encoding utf8
}

function Get-FunnelUrl {
    if (-not (Test-Path -LiteralPath $ts)) { return $null }

    $svc = Get-Service -Name 'Tailscale' -ErrorAction SilentlyContinue
    if ($svc -and $svc.Status -ne 'Running') {
        Start-Service -Name 'Tailscale' -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 5
    }

    $st = & $ts status 2>&1 | Out-String
    if ($st -match 'Logged out|Failed to') {
        $up = & $ts up 2>&1 | Out-String
        if ($up -match 'https://login\.tailscale\.com\S+') {
            Set-Hint ("NEED_LOGIN " + $Matches[0])
        }
        return $null
    }

    $fs = & $ts funnel status 2>&1 | Out-String
    if ($fs -notmatch '127\.0\.0\.1:8000') {
        $outF = Join-Path $Logs 'funnel.out.log'
        $errF = Join-Path $Logs 'funnel.err.log'
        Remove-Item $outF, $errF -ErrorAction SilentlyContinue
        Start-Process -FilePath $ts -ArgumentList 'funnel', '--bg', '8000' `
            -RedirectStandardOutput $outF -RedirectStandardError $errF -WindowStyle Hidden

        $deadline = (Get-Date).AddSeconds([Math]::Min($TimeoutSec, 45))
        while ((Get-Date) -lt $deadline) {
            $fs = & $ts funnel status 2>&1 | Out-String
            if ($fs -match '127\.0\.0\.1:8000') { break }
            $joined = ((Get-Content $outF, $errF -ErrorAction SilentlyContinue) -join ' ')
            if ($joined -match '(https://login\.tailscale\.com/\S*funnel\S*)') {
                Set-Hint ("NEED_ENABLE " + $Matches[1])
                return $null
            }
            Start-Sleep -Seconds 2
        }
    }

    if ($fs -notmatch '127\.0\.0\.1:8000') { return $null }

    $json = & $ts status --json 2>&1 | Out-String
    $self = ($json | ConvertFrom-Json).Self
    $dns = [string]$self.DNSName
    if (-not $dns) { return $null }
    return "https://" + $dns.TrimEnd('.')
}

function Get-CloudflaredUrl {
    $log = Join-Path $Logs 'tunnel.log'
    $out = Join-Path $Logs 'tunnel.out.log'
    Remove-Item $log, $out -ErrorAction SilentlyContinue
    Start-Process -FilePath 'cloudflared' -ArgumentList 'tunnel', '--url', 'http://127.0.0.1:8000' `
        -RedirectStandardOutput $out -RedirectStandardError $log -WindowStyle Hidden
    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    while ((Get-Date) -lt $deadline) {
        if (Test-Path -LiteralPath $log) {
            $hit = Select-String -LiteralPath $log -Pattern 'https://[a-z0-9-]+\.trycloudflare\.com' -ErrorAction SilentlyContinue | Select-Object -First 1
            if ($hit -and $hit.Matches.Count -gt 0) { return $hit.Matches[0].Value }
        }
        Start-Sleep -Seconds 1
    }
    return $null
}

$url = Get-FunnelUrl
if ($url) { Save-Url $url; exit 0 }

$url = Get-CloudflaredUrl
if ($url) { Save-Url $url; exit 0 }
exit 1
