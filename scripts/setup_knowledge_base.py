#!/usr/bin/env python3
"""
Script para configurar la base de conocimiento en producción.
Descarga PDFs desde Google Cloud Storage y los indexa.
"""

import os
import sys
from pathlib import Path
from urllib.request import urlretrieve
import asyncio

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def download_from_gcs(gcs_url: str, destination: Path):
    """
    Descarga archivo desde Google Cloud Storage.

    Args:
        gcs_url: URL pública del archivo en GCS
        destination: Ruta de destino local
    """
    print(f"⬇️  Descargando {destination.name}...")
    destination.parent.mkdir(parents=True, exist_ok=True)
    urlretrieve(gcs_url, destination)
    print(f"✅ Descargado: {destination}")


async def setup_knowledge_base():
    """Configura la base de conocimiento desde variables de entorno."""

    # Check if already set up
    kb_path = PROJECT_ROOT / "data" / "knowledge_base"

    # Get GCS configuration from environment
    # Format: SPECIALTY:FILENAME:GCS_URL,SPECIALTY:FILENAME:GCS_URL,...
    gcs_config = os.getenv("GCS_KNOWLEDGE_BASE_FILES", "")

    if not gcs_config:
        print("⚠️  GCS_KNOWLEDGE_BASE_FILES no configurado")
        print("   Para descargar archivos automáticamente, configura:")
        print("   GCS_KNOWLEDGE_BASE_FILES=specialty:file.pdf:https://...,specialty2:file2.pdf:https://...")
        return

    # Parse configuration
    files_to_download = []
    for entry in gcs_config.split(","):
        parts = entry.strip().split(":")
        if len(parts) == 3:
            specialty, filename, url = parts
            files_to_download.append((specialty, filename, url))

    # Download files
    for specialty, filename, url in files_to_download:
        destination = kb_path / specialty / filename
        if destination.exists():
            print(f"⏭️  Ya existe: {destination}")
            continue
        download_from_gcs(url, destination)

    # Index documents
    if files_to_download:
        print("\n📚 Indexando documentos...")
        from motor.motor_asyncio import AsyncIOMotorClient
        from app.models.database import init_db
        from app.rag.document_indexer import indexer
        from app.config.settings import settings

        # Initialize MongoDB
        client = AsyncIOMotorClient(settings.mongodb_url)
        database = client[settings.mongodb_db_name]
        await init_db(database)

        # Index all
        await indexer.index_all()

        # Close connection
        client.close()

        print("✅ Base de conocimiento configurada")


if __name__ == "__main__":
    asyncio.run(setup_knowledge_base())
