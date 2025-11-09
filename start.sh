#!/bin/bash
set -e

echo "🚀 Starting Clinical Crew API with Gemini File Search..."

# Use PORT environment variable from Render, default to 8000
PORT=${PORT:-8000}

echo "📡 Port: $PORT"
echo "🌍 Environment: ${ENVIRONMENT:-production}"
echo "🔍 RAG Backend: Gemini File Search (${USE_FILE_SEARCH:-true})"

# File Search is managed via Gemini API - no local setup needed
echo "✅ Using Gemini File Search (no local storage required)"

# Start the FastAPI application with production settings
echo "🎯 Starting FastAPI server on port $PORT..."
exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port "$PORT" \
    --workers 2 \
    --log-level info \
    --no-access-log
