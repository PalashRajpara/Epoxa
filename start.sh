#!/usr/bin/env bash

# AI Voice Agent - Multi-Service Startup Script

echo "================================================"
echo "  Starting AI Voice Agent System"
echo "================================================"
echo ""

# Ensure we are in project root
PROJECT_ROOT="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$PROJECT_ROOT"

# Check if tmux is installed for single-window session management
if command -v tmux &> /dev/null; then
    # Kill any existing session to avoid duplicate windows/ports
    tmux kill-session -t voice-ai 2>/dev/null
    
    echo "Creating fresh tmux session 'voice-ai' with all services..."
    tmux new-session -d -s voice-ai -n 'Backend' "cd '$PROJECT_ROOT' && backend/venv/bin/python backend/main.py"
    tmux new-window -t voice-ai -n 'Agent' "cd '$PROJECT_ROOT/agent' && ../agent/venv/bin/python main.py dev"
    tmux new-window -t voice-ai -n 'Frontend' "cd '$PROJECT_ROOT/frontend' && npm start"
    tmux new-window -t voice-ai -n 'Dashboard' "cd '$PROJECT_ROOT/dashboard' && npm start"

    echo "✅ All 4 services started inside tmux session 'voice-ai'!"
    echo "Attach to session with: tmux attach-session -t voice-ai"
    echo "To stop all services: tmux kill-session -t voice-ai"
    exit 0
fi

echo "Tip: Install 'tmux' to launch all services in a single terminal session."
echo ""
echo "Please run the following commands in separate Terminal tabs/windows:"
echo ""
echo "--- Terminal 1: Backend Server ---"
echo "cd $PROJECT_ROOT && backend/venv/bin/python backend/main.py"
echo ""
echo "--- Terminal 2: Voice Agent ---"
echo "cd $PROJECT_ROOT/agent && ../agent/venv/bin/python main.py dev"
echo ""
echo "--- Terminal 3: Frontend (Customer Web UI) ---"
echo "cd $PROJECT_ROOT/frontend && npm start"
echo ""
echo "--- Terminal 4: Admin Dashboard ---"
echo "cd $PROJECT_ROOT/dashboard && npm start"
echo ""
