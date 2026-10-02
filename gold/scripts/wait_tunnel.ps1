param(
    [Parameter(Mandatory = $true)][string]$Log,
    [Parameter(Mandatory = $true)][string]$Out,
    [int]$TimeoutSec = 60
)

# Doi cloudflared in link quick tunnel ra log, ghi vao $Out.
# Exit 0 = tim thay, exit 1 = het thoi gian.
$pattern = 'https://[a-z0-9-]+\.trycloudflare\.com'
$deadline = (Get-Date).AddSeconds($TimeoutSec)

while ((Get-Date) -lt $deadline) {
    if (Test-Path -LiteralPath $Log) {
        $hit = Select-String -LiteralPath $Log -Pattern $pattern -ErrorAction SilentlyContinue |
            Select-Object -First 1
        if ($hit -and $hit.Matches.Count -gt 0) {
            $url = $hit.Matches[0].Value
            Set-Content -LiteralPath $Out -Value $url -NoNewline -Encoding ascii
            exit 0
        }
    }
    Start-Sleep -Seconds 1
}
exit 1
