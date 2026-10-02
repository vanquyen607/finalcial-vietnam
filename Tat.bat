@echo off
setlocal
title Aurum Terminal - Tat
rem =========================================================
rem  Tat Aurum Terminal: dung tunnel Cloudflare + app FastAPI.
rem  Chi dung tien trinh dang lang nghe port 8000 (khong anh
rem  huong den cac cua so python khac cua ban).
rem =========================================================

echo ==================================================
echo    AURUM TERMINAL - TAT
echo ==================================================
echo.

rem ---------- 0) Dung watchdog truoc (khong thi no khoi dong lai app) ----------
powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'powershell.exe' -and $_.CommandLine -like '*watchdog.ps1*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }" < nul
del "D:\Desktop\finan\gold\_logs\watchdog.pid" >nul 2>&1
echo [ OK ] Da dung watchdog.

rem ---------- 0b) Tat duong cong khai (Tailscale Funnel) ----------
powershell -NoProfile -Command "& 'C:\Program Files\Tailscale\tailscale.exe' funnel reset | Out-Null" < nul
echo [ OK ] Da tat funnel (link ts.net ngung hoat dong).

rem ---------- 1) Dung tunnel ----------
tasklist /fi "imagename eq cloudflared.exe" 2>nul | findstr /i "cloudflared.exe" >nul
if errorlevel 1 goto noTunnel
taskkill /f /im cloudflared.exe >nul 2>&1
echo [ OK ] Da dung tunnel.
goto stopApp
:noTunnel
echo [ .. ] Tunnel khong chay.

:stopApp
rem ---------- 2) Dung app (chi PID dang chiem port 8000) ----------
set "PID8000="
for /f %%P in ('powershell -NoProfile -Command "(Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue).OwningProcess | Select-Object -Unique"') do set "PID8000=%%P"
if defined PID8000 goto killApp
echo [ .. ] App khong chay.
goto check

:killApp
taskkill /f /pid %PID8000% >nul 2>&1
ping -n 2 127.0.0.1 >nul
echo [ OK ] Da dung app (PID %PID8000%).

:check
curl -s -o nul -m 3 http://127.0.0.1:8000/api/health
if errorlevel 1 goto alldown
echo [ CANH BAO ] Con dang lang nghe port 8000 - co the la tien trinh khac.
goto end

:alldown
echo.
echo --------------------------------------------------
echo   Tat het. Mo lai: chay KhoiChay.bat (hoac shortcut
echo   "Aurum Terminal" tren Desktop).
echo --------------------------------------------------
:end
echo.
pause
exit /b 0
