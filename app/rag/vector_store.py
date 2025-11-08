"""
Vector Store usando ChromaDB.
"""
import chromadb
from chromadb.config import Settings as ChromaSettings
from typing import List, Dict, Any, Optional
from pathlib import Path

from app.config.settings import settings
from app.rag.embeddings import GeminiEmbeddings


class VectorStore:
    """Wrapper para ChromaDB con Gemini embeddings"""

    def __init__(self, persist_directory: Optional[str] = None):
        """
        Inicializa el vector store.

        Args:
            persist_directory: Directorio de persistencia (usa settings por defecto)
        """
        self.persist_directory = persist_directory or settings.chroma_persist_directory

        # Crear directorio si no existe
        Path(self.persist_directory).mkdir(parents=True, exist_ok=True)

        # Inicializar ChromaDB
        self.client = chromadb.PersistentClient(
            path=self.persist_directory,
            settings=ChromaSettings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )

        # Inicializar embeddings
        self.embeddings = GeminiEmbeddings()

    def get_or_create_collection(self, name: str, metadata: Optional[Dict] = None):
        """
        Obtiene o crea una colección.

        Args:
            name: Nombre de la colección
            metadata: Metadata de la colección

        Returns:
            Colección de ChromaDB
        """
        collection_name = f"{settings.chroma_collection_prefix}_{name}"

        try:
            collection = self.client.get_collection(name=collection_name)
        except Exception:
            collection = self.client.create_collection(
                name=collection_name,
                metadata=metadata or {}
            )

        return collection

    def add_documents(
        self,
        collection_name: str,
        documents: List[str],
        metadatas: List[Dict[str, Any]],
        ids: List[str]
    ):
        """
        Agrega documentos a una colección.

        Args:
            collection_name: Nombre de la colección
            documents: Lista de textos
            metadatas: Lista de metadatos
            ids: Lista de IDs únicos
        """
        collection = self.get_or_create_collection(collection_name)

        # Generar embeddings
        embeddings = self.embeddings.embed_documents(documents)

        # Agregar a la colección
        collection.add(
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )

    def query(
        self,
        collection_name: str,
        query_text: str,
        n_results: int = 5,
        where: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Realiza una búsqueda en la colección.

        Args:
            collection_name: Nombre de la colección
            query_text: Texto de búsqueda
            n_results: Número de resultados
            where: Filtros de metadata

        Returns:
            Resultados de la búsqueda
        """
        collection = self.get_or_create_collection(collection_name)

        # Generar embedding de la query
        query_embedding = self.embeddings.embed_query(query_text)

        # Realizar búsqueda
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where
        )

        return results

    def delete_collection(self, collection_name: str):
        """
        Elimina una colección.

        Args:
            collection_name: Nombre de la colección
        """
        full_name = f"{settings.chroma_collection_prefix}_{collection_name}"
        self.client.delete_collection(name=full_name)

    def get_collection_stats(self, collection_name: str) -> Dict[str, Any]:
        """
        Obtiene estadísticas de una colección.

        Args:
            collection_name: Nombre de la colección

        Returns:
            Estadísticas de la colección
        """
        collection = self.get_or_create_collection(collection_name)

        return {
            "name": collection.name,
            "count": collection.count(),
            "metadata": collection.metadata
        }

    def list_collections(self) -> List[str]:
        """
        Lista todas las colecciones.

        Returns:
            Lista de nombres de colecciones
        """
        collections = self.client.list_collections()
        return [col.name for col in collections]

    def update_document(
        self,
        collection_name: str,
        document_id: str,
        document: str,
        metadata: Dict[str, Any]
    ):
        """
        Actualiza un documento en la colección.

        Args:
            collection_name: Nombre de la colección
            document_id: ID del documento
            document: Nuevo texto
            metadata: Nueva metadata
        """
        collection = self.get_or_create_collection(collection_name)

        # Generar nuevo embedding
        embedding = self.embeddings.embed_documents([document])[0]

        # Actualizar
        collection.update(
            ids=[document_id],
            embeddings=[embedding],
            documents=[document],
            metadatas=[metadata]
        )

    def delete_document(self, collection_name: str, document_id: str):
        """
        Elimina un documento de la colección.

        Args:
            collection_name: Nombre de la colección
            document_id: ID del documento
        """
        collection = self.get_or_create_collection(collection_name)
        collection.delete(ids=[document_id])


# Instancia global del vector store
vector_store = VectorStore()
