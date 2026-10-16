@echo off
chcp 65001 >nul
title Dong Phan Tich Co Phieu
powershell -NoProfile -Command "$c = Get-NetTCPConnection -LocalPort 8100 -State Listen -ErrorAction SilentlyContinue; if ($c) { $c | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }; Write-Host '  [OK] Da dong app Phan Tich Co Phieu.' } else { Write-Host '  App khong dang chay.' }"
ping -n 4 127.0.0.1 >nul 2>nul
exit /b 0
