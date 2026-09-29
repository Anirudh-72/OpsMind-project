@echo off
title Stop OpsMind
cd /d "%~dp0"

echo ============================================================
echo   Stopping OpsMind Server...
echo ============================================================
echo.

:: Kill any process listening on port 8000
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8000') do (
    taskkill /F /PID %%a >nul 2>&1
)

echo Port 8000 released. OpsMind server is stopped.
echo.
timeout /t 2 >nul
