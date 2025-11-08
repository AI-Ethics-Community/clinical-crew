"""
Sistema RAG (Retrieval Augmented Generation).
"""
from app.rag.embeddings import GeminiEmbeddings
from app.rag.vector_store import VectorStore, vector_store
from app.rag.document_indexer import DocumentIndexer, indexer
from app.rag.retriever import RAGRetriever, retriever, DocumentChunk

__all__ = [
    "GeminiEmbeddings",
    "VectorStore",
    "vector_store",
    "DocumentIndexer",
    "indexer",
    "RAGRetriever",
    "retriever",
    "DocumentChunk",
]
