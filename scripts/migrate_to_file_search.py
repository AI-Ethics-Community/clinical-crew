#!/usr/bin/env python3
"""
Migration script to upload documents from local knowledge base to Gemini File Search.
This replaces ChromaDB with Google's managed File Search service.

Usage:
    python scripts/migrate_to_file_search.py --all
    python scripts/migrate_to_file_search.py --specialty cardiology
"""

import asyncio
import sys
from pathlib import Path
from typing import List

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.services.file_search_service import file_search_service
from app.config.settings import settings


def upload_specialty_documents(specialty: str) -> List[str]:
    """
    Upload all documents for a specialty to File Search.

    Args:
        specialty: Specialty name

    Returns:
        List of uploaded document IDs
    """
    knowledge_base_path = Path(settings.knowledge_base_path)
    specialty_path = knowledge_base_path / specialty

    if not specialty_path.exists():
        print(f"⚠️  Directory not found: {specialty_path}")
        return []

    # Supported extensions
    extensions = [".pdf", ".docx", ".md", ".txt"]

    uploaded_docs = []

    print(f"\n📚 Uploading documents for {specialty}...")

    for ext in extensions:
        for file_path in specialty_path.glob(f"*{ext}"):
            try:
                # Prepare metadata
                metadata = {
                    "specialty": specialty,
                    "file_type": ext[1:],  # Remove dot
                }

                # Upload document
                doc_id = file_search_service.upload_document(
                    file_path=file_path,
                    specialty=specialty,
                    display_name=file_path.name,
                    metadata=metadata,
                )

                uploaded_docs.append(doc_id)

            except Exception as e:
                print(f"❌ Error uploading {file_path.name}: {str(e)}")

    print(f"✅ {specialty}: {len(uploaded_docs)} documents uploaded")
    return uploaded_docs


def upload_all_documents():
    """Upload all documents from all specialties."""
    knowledge_base_path = Path(settings.knowledge_base_path)

    if not knowledge_base_path.exists():
        print(f"❌ Knowledge base directory not found: {knowledge_base_path}")
        return

    total_uploaded = 0

    # Get all specialty directories
    for specialty_dir in knowledge_base_path.iterdir():
        if specialty_dir.is_dir() and not specialty_dir.name.startswith("."):
            specialty = specialty_dir.name
            docs = upload_specialty_documents(specialty)
            total_uploaded += len(docs)

    print(f"\n🎉 Migration complete! Total documents uploaded: {total_uploaded}")


def list_existing_stores():
    """List all existing File Search stores."""
    print("\n📋 Existing File Search stores:")
    stores = file_search_service.list_stores()

    if not stores:
        print("   No stores found")
        return

    for store in stores:
        print(f"   • {store['display_name']} ({store['name']})")


def test_retrieval(specialty: str, query: str):
    """
    Test retrieval from a specialty store.

    Args:
        specialty: Specialty name
        query: Test query
    """
    print(f"\n🔍 Testing retrieval for {specialty}...")
    print(f"   Query: {query}")

    # Use File Search generate_with_file_search method
    response_text, citations = file_search_service.generate_with_file_search(
        query=f"Busca información sobre: {query}",
        specialty=specialty,
        system_instruction="Eres un asistente médico. Proporciona información relevante y concisa basada en las guías clínicas."
    )

    print(f"\n   Found {len(citations)} citations")
    print(f"\n   Response preview:")
    print(f"   {response_text[:500]}...")

    if citations:
        print(f"\n   Citations:")
        for citation in citations:
            filename = citation.metadata.get('filename', 'Unknown')
            score = citation.score
            print(f"   • {filename} (confidence: {score:.3f})")
    else:
        print(f"\n   No citations found (File Search may not always include explicit citations)")


def main():
    """Main migration function."""
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python scripts/migrate_to_file_search.py --all")
        print("  python scripts/migrate_to_file_search.py --specialty SPECIALTY")
        print("  python scripts/migrate_to_file_search.py --list")
        print("  python scripts/migrate_to_file_search.py --test SPECIALTY QUERY")
        sys.exit(1)

    command = sys.argv[1]

    if command == "--all":
        print("🚀 Starting migration to Gemini File Search...")
        print(f"📁 Knowledge base: {settings.knowledge_base_path}")
        upload_all_documents()

    elif command == "--specialty" and len(sys.argv) > 2:
        specialty = sys.argv[2]
        print(f"🚀 Uploading documents for {specialty}...")
        upload_specialty_documents(specialty)

    elif command == "--list":
        list_existing_stores()

    elif command == "--test" and len(sys.argv) > 3:
        specialty = sys.argv[2]
        query = " ".join(sys.argv[3:])
        test_retrieval(specialty, query)

    else:
        print("❌ Invalid command")
        print("Use --all, --specialty SPECIALTY, --list, or --test SPECIALTY QUERY")


if __name__ == "__main__":
    main()
