"""
Vector Store using ChromaDB.
"""

import chromadb
from chromadb.config import Settings as ChromaSettings
from typing import List, Dict, Any, Optional
from pathlib import Path

from app.config.settings import settings
from app.rag.embeddings import GeminiEmbeddings


class VectorStore:
    """Wrapper for ChromaDB with Gemini embeddings"""

    def __init__(self, persist_directory: Optional[str] = None):
        """
        Initialize the vector store.

        Args:
            persist_directory: Persistence directory (uses settings default if not provided)
        """
        self.persist_directory = persist_directory or settings.chroma_persist_directory

        # Create directory if it doesn't exist
        Path(self.persist_directory).mkdir(parents=True, exist_ok=True)

        # Initialize ChromaDB
        self.client = chromadb.PersistentClient(
            path=self.persist_directory,
            settings=ChromaSettings(
                anonymized_telemetry=False,
                allow_reset=True,
                chroma_telemetry_impl="none",  # Disable telemetry to avoid capture() argument error
            ),
        )

        # Initialize embeddings
        self.embeddings = GeminiEmbeddings()

    def get_or_create_collection(self, name: str, metadata: Optional[Dict] = None):
        """
        Get or create a collection.

        Args:
            name: Collection name (specialty name without prefix)
            metadata: Collection metadata

        Returns:
            ChromaDB collection
        """
        # Normalize collection name - avoid double prefix
        if name.startswith(f"{settings.chroma_collection_prefix}_"):
            # Already has prefix, use as-is
            collection_name = name
            specialty_name = name.replace(f"{settings.chroma_collection_prefix}_", "")
        else:
            # Add prefix
            collection_name = f"{settings.chroma_collection_prefix}_{name}"
            specialty_name = name

        try:
            collection = self.client.get_collection(name=collection_name)
        except Exception:
            # ChromaDB requires at least one metadata field
            collection_metadata = metadata or {"specialty": specialty_name}
            collection = self.client.create_collection(
                name=collection_name, metadata=collection_metadata
            )

        return collection

    def add_documents(
        self,
        collection_name: str,
        documents: List[str],
        metadatas: List[Dict[str, Any]],
        ids: List[str],
    ):
        """
        Add documents to a collection.

        Args:
            collection_name: Collection name
            documents: List of texts
            metadatas: List of metadata
            ids: List of unique IDs
        """
        collection = self.get_or_create_collection(collection_name)

        # Generate embeddings
        embeddings = self.embeddings.embed_documents(documents)

        # Add to collection
        # Type ignore: ChromaDB's type stubs don't match actual implementation
        collection.add(
            embeddings=embeddings,  # type: ignore[arg-type]
            documents=documents,
            metadatas=metadatas,  # type: ignore[arg-type]
            ids=ids,
        )

    def query(
        self,
        collection_name: str,
        query_text: str,
        n_results: int = 5,
        where: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Perform a search in the collection.

        Args:
            collection_name: Collection name
            query_text: Search text
            n_results: Number of results
            where: Metadata filters

        Returns:
            Search results
        """
        collection = self.get_or_create_collection(collection_name)

        # Generate query embedding
        query_embedding = self.embeddings.embed_query(query_text)

        # Perform search
        # Type ignore: ChromaDB's type stubs don't match actual implementation
        results = collection.query(
            query_embeddings=[query_embedding],  # type: ignore[arg-type]
            n_results=n_results,
            where=where,
        )

        return results  # type: ignore[return-value]

    def delete_collection(self, collection_name: str):
        """
        Delete a collection.

        Args:
            collection_name: Collection name
        """
        full_name = f"{settings.chroma_collection_prefix}_{collection_name}"
        self.client.delete_collection(name=full_name)

    def get_collection_stats(self, collection_name: str) -> Dict[str, Any]:
        """
        Get collection statistics.

        Args:
            collection_name: Collection name

        Returns:
            Collection statistics
        """
        collection = self.get_or_create_collection(collection_name)

        return {
            "name": collection.name,
            "count": collection.count(),
            "metadata": collection.metadata,
        }

    def list_collections(self) -> List[str]:
        """
        List all collections.

        Returns:
            List of collection names
        """
        collections = self.client.list_collections()
        return [col.name for col in collections]

    def update_document(
        self,
        collection_name: str,
        document_id: str,
        document: str,
        metadata: Dict[str, Any],
    ):
        """
        Update a document in the collection.

        Args:
            collection_name: Collection name
            document_id: Document ID
            document: New text
            metadata: New metadata
        """
        collection = self.get_or_create_collection(collection_name)

        # Generate new embedding
        embedding = self.embeddings.embed_documents([document])[0]

        # Update
        # Type ignore: ChromaDB's type stubs don't match actual implementation
        collection.update(
            ids=[document_id],
            embeddings=[embedding],  # type: ignore[arg-type]
            documents=[document],
            metadatas=[metadata],  # type: ignore[list-item]
        )

    def delete_document(self, collection_name: str, document_id: str):
        """
        Delete a document from the collection.

        Args:
            collection_name: Collection name
            document_id: Document ID
        """
        collection = self.get_or_create_collection(collection_name)
        collection.delete(ids=[document_id])


# Lazy initialization wrapper to avoid ChromaDB initialization when using File Search
class LazyVectorStore:
    """
    Lazy proxy for VectorStore that only initializes when accessed.
    This prevents ChromaDB from starting when use_file_search=True.
    """

    def __init__(self):
        self._instance: Optional[VectorStore] = None

    def _get_instance(self) -> VectorStore:
        """Get or create the VectorStore instance."""
        if settings.use_file_search:
            raise RuntimeError(
                "ChromaDB vector store is disabled when use_file_search=True. "
                "Use Gemini File Search API instead."
            )

        if self._instance is None:
            self._instance = VectorStore()

        return self._instance

    def __getattr__(self, name: str):
        """Proxy all attribute access to the actual VectorStore."""
        return getattr(self._get_instance(), name)


# Global vector store instance (uses lazy initialization)
vector_store = LazyVectorStore()  # type: ignore[assignment]
