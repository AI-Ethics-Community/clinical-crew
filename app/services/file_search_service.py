"""
File Search service using Gemini File Search API.
Replaces ChromaDB for RAG retrieval in production.
"""

import time
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass

from google import genai
from google.genai import types

from app.config.settings import settings


@dataclass
class FileSearchChunk:
    """Represents a retrieved document chunk from File Search"""

    content: str
    metadata: Dict[str, Any]
    score: float  # Relevance/confidence score

    def __repr__(self) -> str:
        return f"<FileSearchChunk from={self.metadata.get('filename')} score={self.score:.3f}>"


class FileSearchService:
    """
    Service for managing File Search stores and retrieval.
    Replaces ChromaDB with Google's managed File Search.

    File Search works differently than traditional RAG:
    - The LLM automatically searches the store when you pass it as a tool
    - Returns grounded responses with automatic citations
    - No manual retrieval step needed
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize File Search service.

        Args:
            api_key: Gemini API key (defaults to settings)
        """
        self.api_key = api_key or settings.gemini_api_key
        self.client = genai.Client(api_key=self.api_key)
        self._stores_cache: Dict[str, str] = {}  # specialty -> store_name

    def create_store(self, specialty: str, display_name: Optional[str] = None) -> str:
        """
        Create a File Search store for a specialty.

        Args:
            specialty: Medical specialty name
            display_name: Optional display name

        Returns:
            Store name (ID)
        """
        if specialty in self._stores_cache:
            return self._stores_cache[specialty]

        display_name = display_name or f"clinical_crew_{specialty}"

        store = self.client.file_search_stores.create(
            config={"display_name": display_name}
        )

        self._stores_cache[specialty] = store.name
        return store.name

    def get_or_create_store(self, specialty: str) -> str:
        """
        Get existing store or create new one.

        Args:
            specialty: Medical specialty name

        Returns:
            Store name (ID)
        """
        if specialty in self._stores_cache:
            return self._stores_cache[specialty]

        # Try to find existing store by display name
        display_name = f"clinical_crew_{specialty}"

        try:
            for store in self.client.file_search_stores.list():
                if store.display_name == display_name:
                    self._stores_cache[specialty] = store.name
                    return store.name
        except Exception as e:
            print(f"Warning: Could not list stores: {e}")

        # Create new store
        return self.create_store(specialty, display_name)

    def upload_document(
        self,
        file_path: Path,
        specialty: str,
        display_name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Upload and index a document to File Search.

        Args:
            file_path: Path to document
            specialty: Medical specialty
            display_name: Display name for file
            metadata: Custom metadata

        Returns:
            Operation name
        """
        store_name = self.get_or_create_store(specialty)

        display_name = display_name or file_path.name

        # Detect mime type from extension
        mime_types = {
            '.pdf': 'application/pdf',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.md': 'text/markdown',
            '.txt': 'text/plain',
        }
        mime_type = mime_types.get(file_path.suffix.lower(), 'application/octet-stream')

        # Prepare config
        config: Dict[str, Any] = {
            "display_name": display_name,
            "mime_type": mime_type
        }

        # Add custom metadata if provided
        if metadata:
            custom_metadata = []
            for key, value in metadata.items():
                if isinstance(value, str):
                    custom_metadata.append({"key": key, "string_value": value})
                elif isinstance(value, (int, float)):
                    custom_metadata.append({"key": key, "numeric_value": float(value)})
            if custom_metadata:
                config["custom_metadata"] = custom_metadata

        # Upload and import - use file handle to preserve unicode filenames
        with open(file_path, 'rb') as f:
            operation = self.client.file_search_stores.upload_to_file_search_store(
                file=f, file_search_store_name=store_name, config=config
            )

        # Wait for completion
        while not operation.done:
            time.sleep(2)
            operation = self.client.operations.get(operation)

        print(f"✅ Uploaded: {file_path.name} to {specialty}")
        return operation.name

    def get_file_search_tool(
        self,
        specialty: str,
        metadata_filter: Optional[str] = None,
    ) -> types.Tool:
        """
        Get File Search tool configuration for a specialty.

        This tool is passed to generate_content() and allows the LLM
        to automatically search the file search store.

        Args:
            specialty: Medical specialty
            metadata_filter: Optional metadata filter

        Returns:
            File Search tool configuration
        """
        store_name = self.get_or_create_store(specialty)

        file_search_config = types.FileSearch(
            file_search_store_names=[store_name],
        )

        if metadata_filter:
            file_search_config.metadata_filter = metadata_filter

        return types.Tool(file_search=file_search_config)

    def extract_citations(self, response) -> List[FileSearchChunk]:
        """
        Extract citations from a File Search response.

        Args:
            response: Response from generate_content with File Search

        Returns:
            List of chunks with citations
        """
        chunks: List[FileSearchChunk] = []

        try:
            if not hasattr(response, "candidates") or not response.candidates:
                return chunks

            candidate = response.candidates[0]

            if not hasattr(candidate, "grounding_metadata"):
                return chunks

            grounding = candidate.grounding_metadata

            if not hasattr(grounding, "grounding_chunks"):
                return chunks

            for chunk in grounding.grounding_chunks:
                # Extract content and metadata from grounding chunk
                if hasattr(chunk, "retrieved_context"):
                    # File Search source
                    content = chunk.retrieved_context.text if hasattr(chunk.retrieved_context, "text") else ""
                    title = chunk.retrieved_context.title if hasattr(chunk.retrieved_context, "title") else "Unknown"

                    metadata = {
                        "source": "file_search",
                        "filename": title,
                    }

                    # URI if available
                    if hasattr(chunk.retrieved_context, "uri"):
                        metadata["uri"] = chunk.retrieved_context.uri

                    # Get confidence score if available
                    score = float(chunk.confidence_score) if hasattr(chunk, "confidence_score") else 0.0

                    chunks.append(
                        FileSearchChunk(content=content, metadata=metadata, score=score)
                    )

        except Exception as e:
            print(f"Warning: Could not extract citations: {e}")

        return chunks

    def generate_with_file_search(
        self,
        query: str,
        specialty: str,
        system_instruction: Optional[str] = None,
        metadata_filter: Optional[str] = None,
    ) -> Tuple[str, List[FileSearchChunk]]:
        """
        Generate content using File Search tool.

        The LLM automatically searches the file search store and
        grounds its response with citations.

        Args:
            query: Question or prompt
            specialty: Medical specialty
            system_instruction: Optional system instruction
            metadata_filter: Optional metadata filter

        Returns:
            Tuple of (response_text, citations)
        """
        tool = self.get_file_search_tool(specialty, metadata_filter)

        config_params = {"tools": [tool]}

        if system_instruction:
            config_params["system_instruction"] = system_instruction

        response = self.client.models.generate_content(
            model=settings.gemini_flash_model,
            contents=query,
            config=types.GenerateContentConfig(**config_params),
        )

        response_text = response.text if hasattr(response, "text") else ""
        citations = self.extract_citations(response)

        return response_text, citations

    def format_context(self, chunks: List[FileSearchChunk]) -> str:
        """
        Format retrieved chunks into context for LLM.

        Args:
            chunks: List of chunks

        Returns:
            Formatted context string
        """
        if not chunks:
            return "No se encontró información relevante en la base de conocimiento."

        context_parts: List[str] = []

        for i, chunk in enumerate(chunks, 1):
            source = chunk.metadata.get("filename", "Fuente desconocida")
            context_parts.append(f"[Fuente {i}: {source}]\n{chunk.content}")

        return "\n\n" + "\n\n---\n\n".join(context_parts)

    def get_sources(self, chunks: List[FileSearchChunk]) -> List[Dict[str, Any]]:
        """
        Extract sources from chunks with metadata.

        Args:
            chunks: List of chunks

        Returns:
            List of sources with metadata
        """
        sources = []
        seen_sources = set()

        for chunk in chunks:
            filename = chunk.metadata.get("filename", "Unknown Document")

            if filename not in seen_sources:
                seen_sources.add(filename)
                sources.append(
                    {
                        "title": filename,
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

    def list_stores(self) -> List[Dict[str, str]]:
        """
        List all File Search stores.

        Returns:
            List of stores with name and display_name
        """
        stores = []
        for store in self.client.file_search_stores.list():
            stores.append({"name": store.name, "display_name": store.display_name})
        return stores

    def delete_store(self, specialty: str, force: bool = True):
        """
        Delete a File Search store.

        Args:
            specialty: Medical specialty
            force: Force deletion even if not empty
        """
        store_name = self._stores_cache.get(specialty)
        if not store_name:
            store_name = self.get_or_create_store(specialty)

        self.client.file_search_stores.delete(name=store_name, config={"force": force})

        if specialty in self._stores_cache:
            del self._stores_cache[specialty]

        print(f"🗑️  Deleted store for {specialty}")


# Global instance
file_search_service = FileSearchService()
