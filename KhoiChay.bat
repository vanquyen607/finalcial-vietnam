@echo off
setlocal EnableDelayedExpansion
title Aurum Terminal - Khoi chay
rem =========================================================
rem  Khoi chay Aurum Terminal: app FastAPI + Cloudflare tunnel.
rem  Click vao file nay (hoac shortcut tren Desktop) la chay.
rem  Dong cua so nay dong duoc - 2 tien trinh van chay tiep.
rem =========================================================

set "ROOT=%~dp0"
set "API=%ROOT%gold\backend"
set "WEB=%ROOT%gold\frontend"
set "SCRIPTS=%ROOT%gold\scripts"
set "LOGDIR=%ROOT%gold\_logs"
set "LOG=%LOGDIR%\tunnel.log"
set "OUT=%LOGDIR%\tunnel.out.log"
set "URLFILE=%LOGDIR%\url.txt"
set "HEALTH=http://127.0.0.1:8000/api/health"
set "URL="

if not exist "%LOGDIR%" mkdir "%LOGDIR%"

echo ==================================================
echo    AURUM TERMINAL - KHOI CHAY
echo ==================================================
echo.

where python >nul 2>&1
if errorlevel 1 (
  echo [LOI] Khong tim thay "python" trong PATH.
  goto end
)

if exist "%WEB%\dist\index.html" goto distok
echo [CANH BAO] Chua build giao dien - chay  npm run build  trong gold\frontend
echo            Hien tai chi chay API tai http://127.0.0.1:8000
echo.
:distok

rem ---------- 1) App FastAPI ----------
curl -s -o nul -m 3 "%HEALTH%"
if not errorlevel 1 goto appok
echo [ .. ] Dang khoi dong app...
del "%LOGDIR%\app.out.log" "%LOGDIR%\app.err.log" >nul 2>&1
powershell -NoProfile -Command "Start-Process -FilePath python -ArgumentList 'run.py' -WorkingDirectory '%API%' -WindowStyle Minimized -RedirectStandardOutput '%LOGDIR%\app.out.log' -RedirectStandardError '%LOGDIR%\app.err.log'" < nul
set /a N=0
:waitapp
ping -n 2 127.0.0.1 >nul
set /a N+=1
curl -s -o nul -m 3 "%HEALTH%"
if not errorlevel 1 goto appok
if %N% geq 45 goto failapp
goto waitapp
:appok
echo [ OK ] App dang chay:  http://127.0.0.1:8000
echo.

rem ---------- 2) Duong cong khai ----------
del "%URLFILE%" "%LOGDIR%\tunnel.hint.txt" >nul 2>&1
powershell -NoProfile -ExecutionPolicy Bypass -File "%SCRIPTS%\tunnel.ps1" -Logs "%LOGDIR%" -TimeoutSec 60 < nul
if not exist "%URLFILE%" goto failurl
if exist "%LOGDIR%\tunnel.hint.txt" call :hint
set "URL="
set /p URL=<"%URLFILE%"
if not defined URL goto failurl
echo [ OK ] Link public:  !URL!
goto done

:done
rem ---------- 3) Watchdog: tu khoi dong lai app/tunnel neu bi tat ----------
powershell -NoProfile -Command "Start-Process -FilePath powershell -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass','-WindowStyle','Hidden','-File','%SCRIPTS%\watchdog.ps1' -WindowStyle Hidden" < nul
echo [ OK ] Watchdog: tu dong giu app + tunnel song.
echo.
echo --------------------------------------------------
echo   App local   : http://127.0.0.1:8000
echo   Link public : !URL!
echo.
echo   Cua so nay dong duoc - app/tunnel van chay tiep.
echo   Muon DUNG het: chay Tat.bat  (hoac shortcut "Aurum - Tat")
echo   Link co dinh (Tailscale Funnel): https://desktop-uco2224.tailfb154c.ts.net
echo   Log: gold\_logs\{app.err,watchdog,tunnel}.log
echo --------------------------------------------------
echo.
if defined URL start "" "!URL!"
pause
exit /b 0

:failapp
echo [ LOI ] App khong len duoc sau 45s - xem log: gold\_logs\app.err.log
goto end

:hint
echo [ CANH BAO ] Chua dung duong cong CO DINH - hien tai la link fallback (doi moi lan mo lai).
type "%LOGDIR%\tunnel.hint.txt"
echo.
exit /b 0

:failurl
echo [ LOI ] Khong lay duoc link tunnel sau 60s - xem %LOG%
goto end

:end
echo.
pause
exit /b 1
