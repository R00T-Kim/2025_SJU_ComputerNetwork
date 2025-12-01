@echo off
SETLOCAL

echo ==========================================
echo   Simple HTTP Chat - Windows Start Script
echo ==========================================

REM Check for Python
python --version >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python is not installed or not in PATH.
    pause
    EXIT /B 1
)

REM Check for Node.js/NPM
npm --version >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Node.js/npm is not installed or not in PATH.
    pause
    EXIT /B 1
)

echo.
echo [STEP 1/3] Installing frontend dependencies (my-chat-app)...
cd my-chat-app
call npm install
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] npm install failed.
    cd ..
    pause
    EXIT /B 1
)
cd ..

echo.
echo [STEP 2/3] Starting Backend Server...
start "SimpleChat-Backend" cmd /k "python -m src.server"

echo.
echo [STEP 3/3] Starting Frontend Client...
cd my-chat-app
start "SimpleChat-Frontend" cmd /k "npm start"
cd ..

echo.
echo ==========================================
echo   Backend and Frontend servers started.
echo   Close the new windows to stop them.
echo ==========================================
pause