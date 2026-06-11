#!/bin/bash
# Simple startup script for VPS deployment without Docker

echo "=== Starting Hackathon Discovery & Matching Agent on VPS ==="

# Check if we're in the right directory
if [ ! -f "src/main.py" ]; then
    echo "Error: Please run this script from the project root directory"
    exit 1
fi

# Activate virtual environment
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
    echo "✓ Virtual environment activated"
else
    echo "Error: Virtual environment not found. Please run:"
    echo "  python3 -m venv .venv"
    echo "  source .venv/bin/activate"
    echo "  pip install -r requirements.txt"
    exit 1
fi

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "Warning: .env file not found. Please copy .env.example to .env and fill in your values."
    echo "The app may not work correctly without proper configuration."
fi

# Start the application
echo "Starting FastAPI server on http://0.0.0.0:8000"
echo "Press Ctrl+C to stop"
echo ""

# Run the app
uvicorn src.main:app --host 0.0.0.0 --port 8000