"""
RAG Management Script - Index, re-index, and manage knowledge base documents.

Usage:
    python reindex_mongodb.py                    # Index all new documents
    python reindex_mongodb.py --force            # Re-index all (force)
    python reindex_mongodb.py --specialty cardiology  # Index specific specialty
    python reindex_mongodb.py --validate         # Validate consistency
    python reindex_mongodb.py --stats            # Show statistics
"""

import asyncio
from pathlib import Path
from typing import Optional, List, Tuple

from motor.motor_asyncio import AsyncIOMotorClient

from app.config.settings import settings
from app.models.database import DocumentoRAG, init_db
from app.rag.document_indexer import DocumentIndexer
from app.rag.vector_store import vector_store


async def show_statistics():
    """Show RAG system statistics."""
    print("=" * 70)
    print("RAG SYSTEM STATISTICS")
    print("=" * 70)

    # Initialize MongoDB
    client = AsyncIOMotorClient(settings.mongodb_url)
    database = client[settings.mongodb_db_name]
    await init_db(database)

    # MongoDB stats
    total_docs = await DocumentoRAG.count()
    print(f"\n📊 MongoDB Documents: {total_docs}")

    if total_docs > 0:
        # Group by specialty
        pipeline = [
            {
                "$group": {
                    "_id": "$specialty",
                    "count": {"$sum": 1},
                    "total_chunks": {"$sum": "$total_chunks"},
                }
            },
            {"$sort": {"count": -1}},
        ]
        results = await DocumentoRAG.aggregate(pipeline).to_list(None)

        print("\nBy Specialty:")
        for item in results:
            print(
                f"  {item['_id']:20s}: {item['count']:3d} docs, {item['total_chunks']:6d} chunks"
            )

    # ChromaDB stats
    print(f"\n📦 ChromaDB Collections:")
    collections = vector_store.list_collections()

    for col_name in sorted(collections):
        specialty = col_name.replace(f"{settings.chroma_collection_prefix}_", "")
        try:
            stats = vector_store.get_collection_stats(specialty)
            print(f"  {specialty:20s}: {stats['count']:6d} chunks")
        except Exception as e:
            print(f"  {specialty:20s}: Error - {e}")

    client.close()
    print("=" * 70)


async def validate_consistency():
    """Validate MongoDB <-> ChromaDB consistency."""
    print("=" * 70)
    print("VALIDATING CONSISTENCY")
    print("=" * 70)

    client = AsyncIOMotorClient(settings.mongodb_url)
    database = client[settings.mongodb_db_name]
    await init_db(database)

    issues_found = 0

    # Get all MongoDB documents
    docs = await DocumentoRAG.find_all().to_list()
    print(f"\nChecking {len(docs)} MongoDB documents...")

    for doc in docs:
        specialty = doc.specialty
        try:
            collection = vector_store.get_or_create_collection(specialty)

            # Check if all chunks exist in ChromaDB
            for chunk_id in doc.chunk_ids:
                try:
                    result = collection.get(ids=[chunk_id])
                    if not result or not result["ids"]:
                        print(f"  ❌ Missing chunk: {chunk_id} from {doc.filename}")
                        issues_found += 1
                except Exception:
                    print(f"  ❌ Missing chunk: {chunk_id} from {doc.filename}")
                    issues_found += 1

        except Exception as e:
            print(f"  ❌ Error checking {doc.filename}: {e}")
            issues_found += 1

    if issues_found == 0:
        print("\n✅ All checks passed! MongoDB and ChromaDB are consistent.")
    else:
        print(f"\n⚠️  Found {issues_found} consistency issues.")

    client.close()
    print("=" * 70)


async def index_documents(specialty: Optional[str] = None, force: bool = False):
    """
    Index documents from knowledge base.

    Args:
        specialty: Specific specialty to index (None = all)
        force: Force re-indexing even if already indexed
    """
    print("=" * 70)
    print("INDEXING KNOWLEDGE BASE DOCUMENTS")
    print("=" * 70)

    # Initialize MongoDB connection
    client = AsyncIOMotorClient(settings.mongodb_url)
    database = client[settings.mongodb_db_name]
    await init_db(database)

    indexer = DocumentIndexer()
    knowledge_base_path = Path(settings.knowledge_base_path)

    # Check current MongoDB state
    current_count = await DocumentoRAG.count()
    print(f"\nCurrent MongoDB documents: {current_count}")
    print(f"Force re-index: {force}")
    if specialty:
        print(f"Specialty filter: {specialty}")

    # Index all specialties or specific one
    total_indexed = 0
    total_skipped = 0
    total_errors = 0

    specialties_to_process: List[Tuple[str, Path]] = []
    if specialty:
        specialty_dir = knowledge_base_path / specialty
        if specialty_dir.exists() and specialty_dir.is_dir():
            specialties_to_process.append((specialty, specialty_dir))
        else:
            print(f"❌ Specialty directory not found: {specialty_dir}")
            return
    else:
        for specialty_dir in knowledge_base_path.iterdir():
            if specialty_dir.is_dir() and not specialty_dir.name.startswith("."):
                specialties_to_process.append((specialty_dir.name, specialty_dir))

    for spec_name, spec_dir in specialties_to_process:
        print(f"\n{'=' * 70}")
        print(f"Processing: {spec_name}")
        print(f"{'=' * 70}")

        # Get all document files
        extensions = [".pdf", ".docx", ".md", ".txt"]
        files = []
        # Ensure spec_dir is a Path object for glob
        spec_path = Path(spec_dir) if not isinstance(spec_dir, Path) else spec_dir
        for ext in extensions:
            files.extend(list(spec_path.glob(f"*{ext}")))

        print(f"Found {len(files)} files")

        for file_path in files:
            try:
                # Extract text and compute hash
                text = indexer.extract_text(file_path)
                hash_doc = indexer.compute_hash(text)

                # Check if already exists
                existing = await DocumentoRAG.find_one(
                    DocumentoRAG.document_hash == hash_doc
                )

                if existing and not force:
                    print(f"  ⏭️  Skipped: {file_path.name}")
                    total_skipped += 1
                    continue

                if existing and force:
                    # Delete old record and chunks
                    print(f"  🔄 Re-indexing: {file_path.name}")
                    collection = vector_store.get_or_create_collection(spec_name)
                    for chunk_id in existing.chunk_ids:
                        try:
                            vector_store.delete_document(spec_name, chunk_id)
                        except Exception:
                            pass
                    await existing.delete()

                # Index document
                doc = await indexer.index_document(
                    file_path=file_path,
                    specialty=spec_name,
                    metadata={
                        "document_type": "clinical_guideline",
                    },
                )
                total_indexed += 1

            except Exception as e:
                print(f"  ✗ Error: {file_path.name} - {str(e)}")
                total_errors += 1

    print(f"\n{'=' * 70}")
    print(f"SUMMARY")
    print(f"{'=' * 70}")
    print(f"✅ Indexed:  {total_indexed}")
    print(f"⏭️  Skipped:  {total_skipped}")
    print(f"❌ Errors:   {total_errors}")

    # Final count
    final_count = await DocumentoRAG.count()
    print(f"\nMongoDB documents: {current_count} → {final_count}")
    print("=" * 70)

    client.close()


async def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="RAG Management Script - Index and manage knowledge base documents"
    )
    parser.add_argument(
        "--specialty", type=str, help="Index only specific specialty (e.g., cardiology)"
    )
    parser.add_argument(
        "--force", action="store_true", help="Force re-indexing of all documents"
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate MongoDB <-> ChromaDB consistency",
    )
    parser.add_argument(
        "--stats", action="store_true", help="Show RAG system statistics"
    )

    args = parser.parse_args()

    if args.stats:
        await show_statistics()
    elif args.validate:
        await validate_consistency()
    else:
        await index_documents(specialty=args.specialty, force=args.force)


if __name__ == "__main__":
    asyncio.run(main())
