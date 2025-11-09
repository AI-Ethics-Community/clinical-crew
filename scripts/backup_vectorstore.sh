#!/bin/bash
# Backup ChromaDB vectorstore for version control

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
VECTORSTORE_DIR="$PROJECT_ROOT/data/vectorstore"
BACKUP_FILE="$PROJECT_ROOT/vectorstore-backup.tar.gz"

echo "🗜️  Comprimiendo vectorstore..."

cd "$PROJECT_ROOT"
tar -czf "$BACKUP_FILE" -C data vectorstore/

BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
echo "✅ Backup creado: $BACKUP_FILE ($BACKUP_SIZE)"

# Calcular checksum
CHECKSUM=$(sha256sum "$BACKUP_FILE" | cut -d' ' -f1)
echo "$CHECKSUM" > "$BACKUP_FILE.sha256"
echo "🔐 Checksum: $CHECKSUM"

echo ""
echo "Para subir a Git (opcional si es pequeño):"
echo "  git add vectorstore-backup.tar.gz vectorstore-backup.tar.gz.sha256"
echo ""
echo "Para subir a Google Cloud Storage:"
echo "  gsutil cp $BACKUP_FILE gs://YOUR_BUCKET_NAME/"
