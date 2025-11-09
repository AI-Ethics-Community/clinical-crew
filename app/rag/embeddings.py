"""
Embedding client using Google Gemini.
"""

import asyncio
import google.generativeai as genai
from typing import List
from app.config.settings import settings


class GeminiEmbeddings:
    """Client for generating embeddings with Google Gemini"""

    def __init__(self):
        """Initialize Gemini client"""
        genai.configure(api_key=settings.gemini_api_key)
        self.model = settings.chroma_embedding_model

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple documents (synchronous).

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors
        """
        embeddings = []
        for text in texts:
            embedding = genai.embed_content(
                model=self.model, content=text, task_type="retrieval_document"
            )
            embeddings.append(embedding["embedding"])
        return embeddings

    async def embed_documents_async(
        self, texts: List[str], batch_size: int = 10
    ) -> List[List[float]]:
        """
        Generate embeddings for multiple documents (asynchronous with batching).

        Args:
            texts: List of texts to embed
            batch_size: Number of texts to process in parallel

        Returns:
            List of embedding vectors
        """
        embeddings = []

        # Process in batches to avoid rate limits
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]

            # Create async tasks for batch
            tasks = [
                asyncio.to_thread(
                    genai.embed_content,
                    model=self.model,
                    content=text,
                    task_type="retrieval_document",
                )
                for text in batch
            ]

            # Wait for all tasks in batch
            batch_results = await asyncio.gather(*tasks)

            # Extract embeddings from results
            for result in batch_results:
                embeddings.append(result["embedding"])

        return embeddings

    def embed_query(self, text: str) -> List[float]:
        """
        Generate embedding for a search query (synchronous).

        Args:
            text: Query text

        Returns:
            Embedding vector
        """
        embedding = genai.embed_content(
            model=self.model, content=text, task_type="retrieval_query"
        )
        return embedding["embedding"]

    async def embed_query_async(self, text: str) -> List[float]:
        """
        Generate embedding for a search query (asynchronous).

        Args:
            text: Query text

        Returns:
            Embedding vector
        """
        result = await asyncio.to_thread(
            genai.embed_content,
            model=self.model,
            content=text,
            task_type="retrieval_query",
        )
        return result["embedding"]

    def get_embedding_dimension(self) -> int:
        """
        Return the dimension of embeddings.

        Returns:
            Embedding vector dimension
        """
        # Gemini text-embedding-004 generates 768-dimensional embeddings
        return 768
