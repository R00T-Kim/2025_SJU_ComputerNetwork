@echo off
echo [INFO] Starting Backend...
start "Backend" cmd /k "python src/server.py"

echo [INFO] Starting Frontend...
cd my-chat-app
start "Frontend" cmd /k "npm start"
cd ..

echo [INFO] Done.