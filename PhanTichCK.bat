@echo off
chcp 65001 >nul
title Phan Tich Co Phieu
setlocal
set "ROOT=%~dp0stocks"
set "PORT=8100"
cd /d "%ROOT%"

rem --- neu app da chay roi thi chi mo trinh duyet
powershell -NoProfile -Command "(Invoke-WebRequest -UseBasicParsing -Uri 'http://127.0.0.1:8100/api/health' -TimeoutSec 2).StatusCode" >nul 2>nul
if not errorlevel 1 goto :open

rem --- kiem tra python + thu vien
python -c "import fastapi, uvicorn, pandas, vnstock, requests" >nul 2>nul
if errorlevel 1 goto :nodeps

start "PhanTichCK" /min python -m uvicorn backend.main:app --host 127.0.0.1 --port 8100 --log-level warning

rem --- cho app san (toi da ~60s)
set /a tries=0
:wait
ping -n 3 127.0.0.1 >nul 2>nul
set /a tries+=1
powershell -NoProfile -Command "(Invoke-WebRequest -UseBasicParsing -Uri 'http://127.0.0.1:8100/api/health' -TimeoutSec 2).StatusCode" >nul 2>nul
if not errorlevel 1 goto :open
if %tries% geq 30 goto :fail
goto :wait

:open
if /i "%~1"=="noopen" goto :done
start "" "http://127.0.0.1:8100"
goto :done

:nodeps
echo.
echo  [LOI] Thieu Python hoac thu vien. Chay lenh nay roi chay lai:
echo.
echo    python -m pip install -U --extra-index-url https://vnstocks.com/api/simple "vnstock>=4.0.8" fastapi uvicorn pandas requests
echo.
pause
exit /b 1

:fail
echo.
echo  [LOI] App khong khoi duoc. Mo cua so "PhanTichCK" de xem loi, hoac chay thu:
echo.
echo    cd /d "%ROOT%" ^&^& python -m uvicorn backend.main:app --port 8100
echo.
pause
exit /b 1

:done
echo  App dang chay: http://127.0.0.1:8100  (dong bang cach dong cua so PhanTichCK hoac DongPhanTichCK.bat)
ping -n 7 127.0.0.1 >nul 2>nul
exit /b 0
