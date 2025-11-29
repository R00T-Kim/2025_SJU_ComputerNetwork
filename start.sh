#!/usr/bin/env bash
set -euo pipefail

# Root of the repo
ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

echo "-> Installing frontend deps (my-chat-app)..."
npm --prefix my-chat-app install >/tmp/my-chat-app-install.log 2>&1 && echo "   done" || { echo "   install failed; see /tmp/my-chat-app-install.log"; exit 1; }

echo "-> Starting backend (python3 -m src.server)..."
python3 -m src.server &
BACK_PID=$!

echo "-> Starting frontend (npm start in my-chat-app)..."
npm --prefix my-chat-app start &
FRONT_PID=$!

cleanup() {
  echo "-> Stopping servers..."
  kill $BACK_PID $FRONT_PID 2>/dev/null || true
}
trap cleanup EXIT INT TERM

echo "Backend PID: $BACK_PID"
echo "Frontend PID: $FRONT_PID"
echo "Use Ctrl+C to stop both."

# Wait for both to exit (compatible with macOS Bash)
wait $BACK_PID $FRONT_PID
