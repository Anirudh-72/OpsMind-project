@echo off
title OpsMind — Memory-Aware Incident Response Assistant
cd /d "%~dp0"

echo ============================================================
echo   OpsMind — Memory-Aware Incident Response Assistant
echo ============================================================
echo.
echo Checking Python runtime...

set "PYTHON_EXE=python"
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    if exist "%LOCALAPPDATA%\Python\pythoncore-3.14-64\python.exe" (
        set "PYTHON_EXE=%LOCALAPPDATA%\Python\pythoncore-3.14-64\python.exe"
    ) else (
        echo [ERROR] Python was not found on your system!
        echo Please make sure Python 3.10+ is installed.
        echo.
        pause
        exit /b 1
    )
)

echo Starting local server at http://127.0.0.1:8000 ...
echo Opening your web browser automatically in 2 seconds...
echo.
echo ------------------------------------------------------------
echo  KEEP THIS WINDOW OPEN while using OpsMind in your browser.
echo  To STOP the server: Close this window or press Ctrl+C.
echo ------------------------------------------------------------
echo.

:: Automatically open browser after 2 seconds in background
start "" cmd /c "timeout /t 2 /nobreak >nul & start http://127.0.0.1:8000"

:: Start the OpsMind application
"%PYTHON_EXE%" run.py

echo.
echo OpsMind server has stopped.
pause
