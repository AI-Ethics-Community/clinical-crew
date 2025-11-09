#!/bin/bash
set -e

echo "Starting Clinical Crew API..."

# Use PORT environment variable from Render, default to 8000
PORT=${PORT:-8000}

echo "Port: $PORT"
echo "Environment: ${ENVIRONMENT:-production}"

# Run database initialization if needed
# python -m app.rag.document_indexer --all || echo "Skipping indexer (may run separately)"

# Start the FastAPI application with production settings
exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port "$PORT" \
    --workers 2 \
    --log-level info \
    --no-access-log
