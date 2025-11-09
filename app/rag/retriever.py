"""
Retrieval system for RAG.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import hashlib
import json

from app.rag.vector_store import vector_store


@dataclass
class DocumentChunk:
    """Represents a retrieved document chunk"""

    content: str
    metadata: Dict[str, Any]
    score: float  # Distance/similarity

    def __repr__(self) -> str:
        return f"<DocumentChunk from={self.metadata.get('filename')} score={self.score:.3f}>"


class RAGRetriever:
    """Retriever for semantic search in knowledge base"""

    def __init__(self, enable_cache: bool = True, cache_size: int = 1000):
        """
        Initialize retriever.

        Args:
            enable_cache: Enable query result caching
            cache_size: Maximum number of cached queries
        """
        self.vector_store = vector_store
        self.enable_cache = enable_cache
        self.cache_size = cache_size
        self._cache: Dict[str, List[DocumentChunk]] = {}

    def _get_cache_key(self, query: str, specialty: str, top_k: int) -> str:
        """Generate cache key for query."""
        cache_data = f"{query}:{specialty}:{top_k}"
        return hashlib.md5(cache_data.encode()).hexdigest()

    def _get_from_cache(self, cache_key: str) -> Optional[List[DocumentChunk]]:
        """Get cached results if available."""
        if not self.enable_cache:
            return None
        return self._cache.get(cache_key)

    def _add_to_cache(self, cache_key: str, chunks: List[DocumentChunk]):
        """Add results to cache with size limit."""
        if not self.enable_cache:
            return

        # Simple LRU: clear cache if full
        if len(self._cache) >= self.cache_size:
            # Remove oldest 20% of entries
            to_remove = list(self._cache.keys())[: int(self.cache_size * 0.2)]
            for key in to_remove:
                del self._cache[key]

        self._cache[cache_key] = chunks

    def clear_cache(self):
        """Clear all cached results."""
        self._cache.clear()

    def retrieve(
        self,
        query: str,
        specialty: str,
        top_k: int = 5,
        score_threshold: Optional[float] = None,
    ) -> List[DocumentChunk]:
        """
        Retrieve relevant documents for a query.

        Args:
            query: Question or search text
            specialty: Medical specialty
            top_k: Number of results to return
            score_threshold: Minimum similarity threshold (optional)

        Returns:
            List of relevant chunks
        """
        # Check cache first
        cache_key = self._get_cache_key(query, specialty, top_k)
        cached_results = self._get_from_cache(cache_key)
        if cached_results is not None:
            # Apply threshold filter if specified
            if score_threshold is not None:
                return [c for c in cached_results if c.score >= score_threshold]
            return cached_results

        collection_name = specialty.lower()

        # Perform search
        results = self.vector_store.query(
            collection_name=collection_name, query_text=query, n_results=top_k
        )

        # Process results
        chunks: List[DocumentChunk] = []

        if results and results.get("documents"):
            for i in range(len(results["documents"][0])):
                content = results["documents"][0][i]
                metadata = results["metadatas"][0][i]
                distance = results["distances"][0][i]

                # Convert distance to similarity score (1 - normalized distance)
                # ChromaDB uses L2 distance, lower values = more similar
                score = 1 / (1 + distance)

                # Filter by threshold if specified
                if score_threshold is not None and score < score_threshold:
                    continue

                chunks.append(
                    DocumentChunk(content=content, metadata=metadata, score=score)
                )

        # Add to cache
        self._add_to_cache(cache_key, chunks)

        return chunks

    def retrieve_multi_query(
        self,
        queries: List[str],
        specialty: str,
        top_k: int = 5,
        deduplicate: bool = True,
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
                doc_hash = chunk.metadata.get("document_hash")

                if deduplicate and doc_hash in seen_ids:
                    continue

                if doc_hash:
                    seen_ids.add(doc_hash)

                all_chunks.append(chunk)

        # Ordenar por score
        all_chunks.sort(key=lambda x: x.score, reverse=True)

        return all_chunks[: top_k * len(queries)]

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

        context_parts: List[str] = []

        for i, chunk in enumerate(chunks, 1):
            source: str = str(chunk.metadata.get("filename", "Fuente desconocida"))
            chunk_idx: Any = chunk.metadata.get("chunk_index", "")

            context_parts.append(
                f"[Fuente {i}: {source} (fragmento {chunk_idx})]\n{chunk.content}"
            )

        return "\n\n" + "\n\n---\n\n".join(context_parts)

    def get_sources(
        self, chunks: List[DocumentChunk], group_by_document: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Extract sources from chunks with complete metadata.

        Args:
            chunks: List of chunks
            group_by_document: Group multiple chunks from same document

        Returns:
            List of sources with metadata (title, content, metadata, score)
        """
        if not group_by_document:
            # Original behavior: one source per chunk
            sources = []
            seen_chunks = set()

            for chunk in chunks:
                chunk_id = f"{chunk.metadata.get('filename')}_{chunk.metadata.get('chunk_index')}"

                if chunk_id not in seen_chunks:
                    seen_chunks.add(chunk_id)
                    sources.append(
                        {
                            "title": chunk.metadata.get("filename", "Unknown Document"),
                            "content": (
                                chunk.content[:300]
                                if len(chunk.content) > 300
                                else chunk.content
                            ),
                            "metadata": chunk.metadata,
                            "score": chunk.score,
                        }
                    )

            return sources

        # Group chunks by document
        from collections import defaultdict

        docs_dict = defaultdict(list)

        for chunk in chunks:
            filename = chunk.metadata.get("filename", "Unknown Document")
            docs_dict[filename].append(chunk)

        # Create one source per document with aggregated info
        sources = []
        for filename, doc_chunks in docs_dict.items():
            # Sort chunks by relevance
            doc_chunks.sort(key=lambda c: c.score, reverse=True)

            # Use best chunk as representative
            best_chunk = doc_chunks[0]

            # Aggregate content from top chunks
            combined_content = "\n\n".join(
                [
                    f"[Chunk {c.metadata.get('chunk_index')}]: {c.content[:200]}..."
                    for c in doc_chunks[:3]  # Top 3 chunks max
                ]
            )

            # Build metadata dict with explicit typing
            source_metadata: Dict[str, Any] = {
                **best_chunk.metadata,
                "chunks_count": len(doc_chunks),
                "chunk_indices": [c.metadata.get("chunk_index") for c in doc_chunks],
                "avg_score": sum(c.score for c in doc_chunks) / len(doc_chunks),
            }

            source_entry: Dict[str, Any] = {
                "title": filename,
                "content": combined_content[:500],  # Limit total length
                "metadata": source_metadata,
                "score": best_chunk.score,  # Use best score
            }

            sources.append(source_entry)

        # Sort by best score
        sources.sort(key=lambda s: s["score"], reverse=True)

        return sources

    def retrieve_with_context(
        self, query: str, specialty: str, top_k: int = 5, include_sources: bool = True
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

        result: Dict[str, Any] = {
            "context": self.format_context(chunks),
            "chunks_count": len(chunks),
        }

        if include_sources:
            result["sources"] = self.get_sources(chunks)

        return result


# Instancia global del retriever
retriever = RAGRetriever()
