#!/bin/bash
# Restore ChromaDB vectorstore in production

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
VECTORSTORE_DIR="$PROJECT_ROOT/data/vectorstore"
BACKUP_FILE="$PROJECT_ROOT/vectorstore-backup.tar.gz"

# Check if vectorstore already exists
if [ -d "$VECTORSTORE_DIR" ] && [ "$(ls -A $VECTORSTORE_DIR)" ]; then
    echo "✅ Vectorstore ya existe, omitiendo restauración"
    exit 0
fi

echo "📦 Restaurando vectorstore..."

# If backup file doesn't exist locally, try to download from GCS
if [ ! -f "$BACKUP_FILE" ]; then
    if [ -n "$GCS_VECTORSTORE_URL" ]; then
        echo "⬇️  Descargando desde Google Cloud Storage..."
        curl -L "$GCS_VECTORSTORE_URL" -o "$BACKUP_FILE"
    else
        echo "❌ Error: vectorstore-backup.tar.gz no encontrado"
        echo "   Configura GCS_VECTORSTORE_URL o incluye el backup en el repositorio"
        exit 1
    fi
fi

# Verify checksum if available
if [ -f "$BACKUP_FILE.sha256" ]; then
    echo "🔐 Verificando checksum..."
    sha256sum -c "$BACKUP_FILE.sha256"
fi

# Extract
echo "📂 Extrayendo vectorstore..."
cd "$PROJECT_ROOT"
tar -xzf "$BACKUP_FILE"

echo "✅ Vectorstore restaurado exitosamente"
