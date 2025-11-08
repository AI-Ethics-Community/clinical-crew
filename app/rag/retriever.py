"""
Sistema de recuperación (retrieval) para RAG.
"""
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from app.rag.vector_store import vector_store


@dataclass
class DocumentChunk:
    """Representa un chunk de documento recuperado"""
    content: str
    metadata: Dict[str, Any]
    score: float  # Distancia/similitud

    def __repr__(self) -> str:
        return f"<DocumentChunk from={self.metadata.get('filename')} score={self.score:.3f}>"


class RAGRetriever:
    """Retriever para búsqueda semántica en la base de conocimiento"""

    def __init__(self):
        """Inicializa el retriever"""
        self.vector_store = vector_store

    def retrieve(
        self,
        query: str,
        specialty: str,
        top_k: int = 5,
        score_threshold: Optional[float] = None
    ) -> List[DocumentChunk]:
        """
        Recupera documentos relevantes para una query.

        Args:
            query: Pregunta o texto de búsqueda
            specialty: Especialidad médica
            top_k: Número de resultados a retornar
            score_threshold: Umbral mínimo de similitud (opcional)

        Returns:
            Lista de chunks relevantes
        """
        collection_name = specialty.lower()

        # Realizar búsqueda
        results = self.vector_store.query(
            collection_name=collection_name,
            query_text=query,
            n_results=top_k
        )

        # Procesar resultados
        chunks = []

        if results and results.get('documents'):
            for i in range(len(results['documents'][0])):
                content = results['documents'][0][i]
                metadata = results['metadatas'][0][i]
                distance = results['distances'][0][i]

                # Convertir distancia a score de similitud (1 - distancia normalizada)
                # ChromaDB usa distancia L2, valores más bajos = más similar
                score = 1 / (1 + distance)

                # Filtrar por threshold si está especificado
                if score_threshold is not None and score < score_threshold:
                    continue

                chunks.append(DocumentChunk(
                    content=content,
                    metadata=metadata,
                    score=score
                ))

        return chunks

    def retrieve_multi_query(
        self,
        queries: List[str],
        specialty: str,
        top_k: int = 5,
        deduplicate: bool = True
    ) -> List[DocumentChunk]:
        """
        Recupera documentos para múltiples queries (query expansion).

        Args:
            queries: Lista de queries
            specialty: Especialidad médica
            top_k: Número de resultados por query
            deduplicate: Eliminar duplicados

        Returns:
            Lista de chunks relevantes
        """
        all_chunks = []
        seen_ids = set()

        for query in queries:
            chunks = self.retrieve(query, specialty, top_k)

            for chunk in chunks:
                # Deduplicar por hash del documento
                doc_hash = chunk.metadata.get('document_hash')

                if deduplicate and doc_hash in seen_ids:
                    continue

                if doc_hash:
                    seen_ids.add(doc_hash)

                all_chunks.append(chunk)

        # Ordenar por score
        all_chunks.sort(key=lambda x: x.score, reverse=True)

        return all_chunks[:top_k * len(queries)]

    def format_context(self, chunks: List[DocumentChunk]) -> str:
        """
        Formatea los chunks recuperados en un contexto para el LLM.

        Args:
            chunks: Lista de chunks

        Returns:
            Contexto formateado
        """
        if not chunks:
            return "No se encontró información relevante en la base de conocimiento."

        context_parts = []

        for i, chunk in enumerate(chunks, 1):
            source = chunk.metadata.get('filename', 'Fuente desconocida')
            chunk_idx = chunk.metadata.get('chunk_index', '')

            context_parts.append(
                f"[Fuente {i}: {source} (fragmento {chunk_idx})]\n{chunk.content}"
            )

        return "\n\n" + "\n\n---\n\n".join(context_parts)

    def get_sources(self, chunks: List[DocumentChunk]) -> List[str]:
        """
        Extrae las fuentes de los chunks.

        Args:
            chunks: Lista de chunks

        Returns:
            Lista de fuentes únicas
        """
        sources = set()

        for chunk in chunks:
            source = chunk.metadata.get('filename')
            if source:
                sources.add(source)

        return sorted(list(sources))

    def retrieve_with_context(
        self,
        query: str,
        specialty: str,
        top_k: int = 5,
        include_sources: bool = True
    ) -> Dict[str, Any]:
        """
        Recupera documentos y retorna contexto formateado.

        Args:
            query: Pregunta
            specialty: Especialidad
            top_k: Número de resultados
            include_sources: Incluir lista de fuentes

        Returns:
            Diccionario con contexto y metadatos
        """
        chunks = self.retrieve(query, specialty, top_k)

        result = {
            "context": self.format_context(chunks),
            "chunks_count": len(chunks),
        }

        if include_sources:
            result["sources"] = self.get_sources(chunks)

        return result


# Instancia global del retriever
retriever = RAGRetriever()
