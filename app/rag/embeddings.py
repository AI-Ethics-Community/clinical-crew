"""
Cliente de embeddings usando Google Gemini.
"""
import google.generativeai as genai
from typing import List
from app.config.settings import settings


class GeminiEmbeddings:
    """Cliente para generar embeddings con Google Gemini"""

    def __init__(self):
        """Inicializa el cliente de Gemini"""
        genai.configure(api_key=settings.gemini_api_key)
        self.model = settings.chroma_embedding_model

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        Genera embeddings para múltiples documentos.

        Args:
            texts: Lista de textos a embedear

        Returns:
            Lista de vectores de embeddings
        """
        embeddings = []
        for text in texts:
            embedding = genai.embed_content(
                model=self.model,
                content=text,
                task_type="retrieval_document"
            )
            embeddings.append(embedding['embedding'])
        return embeddings

    def embed_query(self, text: str) -> List[float]:
        """
        Genera embedding para una query de búsqueda.

        Args:
            text: Texto de la query

        Returns:
            Vector de embedding
        """
        embedding = genai.embed_content(
            model=self.model,
            content=text,
            task_type="retrieval_query"
        )
        return embedding['embedding']

    def get_embedding_dimension(self) -> int:
        """
        Retorna la dimensión de los embeddings.

        Returns:
            Dimensión del vector de embedding
        """
        # Gemini text-embedding-004 genera embeddings de 768 dimensiones
        return 768
