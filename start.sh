#!/bin/bash
set -e

echo "🚀 Starting Clinical Crew API..."

# Use PORT environment variable from Render, default to 8000
PORT=${PORT:-8000}

echo "📡 Port: $PORT"
echo "🌍 Environment: ${ENVIRONMENT:-production}"

# Restore vectorstore if not present
echo "🔍 Checking vectorstore..."
if [ ! -d "data/vectorstore" ] || [ -z "$(ls -A data/vectorstore)" ]; then
    echo "📦 Vectorstore vacío, restaurando..."
    bash scripts/restore_vectorstore.sh || echo "⚠️  Warning: Vectorstore restore failed"
else
    echo "✅ Vectorstore ya existe"
fi

# Setup knowledge base from GCS if configured
if [ -n "$GCS_KNOWLEDGE_BASE_FILES" ]; then
    echo "📚 Configurando knowledge base..."
    python3 scripts/setup_knowledge_base.py || echo "⚠️  Warning: Knowledge base setup failed"
fi

# Optional: Run full reindexing (only if REINDEX_ON_START=true)
if [ "$REINDEX_ON_START" = "true" ]; then
    echo "🔄 Reindexando documentos..."
    python -m app.rag.document_indexer --all || echo "⚠️  Warning: Reindexing failed"
fi

# Start the FastAPI application with production settings
echo "🎯 Starting FastAPI server on port $PORT..."
exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port "$PORT" \
    --workers 2 \
    --log-level info \
    --no-access-log
