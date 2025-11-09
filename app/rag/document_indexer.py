"""
Sistema de indexación de documentos médicos.
"""
import hashlib
import uuid
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

from pypdf import PdfReader
from docx import Document as DocxDocument
import markdown

from app.rag.vector_store import vector_store
from app.models.database import DocumentoRAG
from app.config.settings import settings


class DocumentIndexer:
    """Indexador de documentos para el sistema RAG"""

    def __init__(self):
        """Inicializa el indexador"""
        self.knowledge_base_path = Path(settings.knowledge_base_path)
        self.chunk_size = 1000  # Caracteres por chunk
        self.chunk_overlap = 200  # Overlap entre chunks

    def extract_text_from_pdf(self, file_path: Path) -> str:
        """
        Extrae texto de un PDF.

        Args:
            file_path: Ruta del archivo PDF

        Returns:
            Texto extraído
        """
        reader = PdfReader(str(file_path))
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n\n"
        return text

    def extract_text_from_docx(self, file_path: Path) -> str:
        """
        Extrae texto de un DOCX.

        Args:
            file_path: Ruta del archivo DOCX

        Returns:
            Texto extraído
        """
        doc = DocxDocument(str(file_path))
        text = ""
        for paragraph in doc.paragraphs:
            text += paragraph.text + "\n\n"
        return text

    def extract_text_from_md(self, file_path: Path) -> str:
        """
        Extrae texto de un Markdown.

        Args:
            file_path: Ruta del archivo MD

        Returns:
            Texto extraído
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            text = f.read()
        return text

    def extract_text_from_txt(self, file_path: Path) -> str:
        """
        Extrae texto de un TXT.

        Args:
            file_path: Ruta del archivo TXT

        Returns:
            Texto extraído
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            text = f.read()
        return text

    def extract_text(self, file_path: Path) -> str:
        """
        Extrae texto de un archivo según su tipo.

        Args:
            file_path: Ruta del archivo

        Returns:
            Texto extraído
        """
        suffix = file_path.suffix.lower()

        extractors = {
            '.pdf': self.extract_text_from_pdf,
            '.docx': self.extract_text_from_docx,
            '.md': self.extract_text_from_md,
            '.txt': self.extract_text_from_txt,
        }

        extractor = extractors.get(suffix)
        if not extractor:
            raise ValueError(f"Tipo de archivo no soportado: {suffix}")

        return extractor(file_path)

    def chunk_text(self, text: str) -> List[str]:
        """
        Divide el texto en chunks con overlap.

        Args:
            text: Texto a dividir

        Returns:
            Lista de chunks
        """
        chunks = []
        start = 0
        text_length = len(text)

        while start < text_length:
            end = start + self.chunk_size
            chunk = text[start:end]

            # Intentar cortar en un punto natural (fin de párrafo o oración)
            if end < text_length:
                # Buscar el último punto seguido de espacio
                last_period = chunk.rfind('. ')
                if last_period > self.chunk_size * 0.5:  # Al menos 50% del chunk
                    end = start + last_period + 1
                    chunk = text[start:end]

            chunks.append(chunk.strip())
            start = end - self.chunk_overlap

        return [c for c in chunks if c]  # Filtrar chunks vacíos

    def compute_hash(self, text: str) -> str:
        """
        Calcula hash del contenido.

        Args:
            text: Texto

        Returns:
            Hash SHA256
        """
        return hashlib.sha256(text.encode()).hexdigest()

    async def index_document(
        self,
        file_path: Path,
        specialty: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> DocumentoRAG:
        """
        Indexa un documento en el sistema RAG.

        Args:
            file_path: Ruta del archivo
            specialty: Especialidad médica
            metadata: Metadata adicional

        Returns:
            Documento indexado
        """
        # Extraer texto
        text = self.extract_text(file_path)
        hash_doc = self.compute_hash(text)

        # Verificar si ya existe
        existing = await DocumentoRAG.find_one(
            DocumentoRAG.document_hash == hash_doc
        )

        if existing and existing.indexado:
            print(f"Documento ya indexado: {file_path.name}")
            return existing

        # Crear chunks
        chunks = self.chunk_text(text)

        # Generar IDs para los chunks
        chunk_ids = [f"{hash_doc}_{i}" for i in range(len(chunks))]

        # Preparar metadata para cada chunk
        chunk_metadatas = []
        for i, chunk in enumerate(chunks):
            chunk_metadata = {
                "specialty": specialty,
                "filename": file_path.name,
                "chunk_index": str(i),  # ChromaDB requires string values
                "total_chunks": str(len(chunks)),  # ChromaDB requires string values
                "document_hash": hash_doc,
            }
            if metadata:
                # Add optional metadata fields as strings
                for key, value in metadata.items():
                    if value is not None:
                        chunk_metadata[key] = str(value)
            chunk_metadatas.append(chunk_metadata)

        # Indexar en ChromaDB
        collection_name = specialty.lower()
        vector_store.add_documents(
            collection_name=collection_name,
            documents=chunks,
            metadatas=chunk_metadatas,
            ids=chunk_ids
        )

        # Guardar en MongoDB
        doc_rag = DocumentoRAG(
            specialty=specialty,
            filename=file_path.name,
            file_path=str(file_path),
            document_type=metadata.get("document_type", "documento") if metadata else "documento",
            titulo=metadata.get("titulo") if metadata else None,
            autor=metadata.get("autor") if metadata else None,
            publication_date=metadata.get("publication_date") if metadata else None,
            fuente=metadata.get("fuente") if metadata else None,
            document_hash=hash_doc,
            chunk_ids=chunk_ids,
            total_chunks=len(chunks),
            indexado=True,
            indexing_date=datetime.utcnow(),
        )

        await doc_rag.insert()

        print(f"✓ Indexado: {file_path.name} ({len(chunks)} chunks)")
        return doc_rag

    async def index_especialidad(self, specialty: str) -> List[DocumentoRAG]:
        """
        Indexa todos los documentos de una specialty.

        Args:
            specialty: Nombre de la specialty

        Returns:
            Lista de documentos indexados
        """
        especialidad_path = self.knowledge_base_path / specialty
        if not especialidad_path.exists():
            print(f"⚠ Directorio no encontrado: {especialidad_path}")
            return []

        documentos_indexados = []

        # Extensiones soportadas
        extensiones = ['.pdf', '.docx', '.md', '.txt']

        for ext in extensiones:
            for file_path in especialidad_path.glob(f"*{ext}"):
                try:
                    doc = await self.index_document(file_path, specialty)
                    documentos_indexados.append(doc)
                except Exception as e:
                    print(f"✗ Error indexando {file_path.name}: {str(e)}")

        return documentos_indexados

    async def index_all(self) -> Dict[str, List[DocumentoRAG]]:
        """
        Indexa todos los documentos de todas las especialidades.

        Returns:
            Diccionario de specialty -> documentos indexados
        """
        resultados = {}

        # Obtener todas las carpetas de especialidades
        for especialidad_dir in self.knowledge_base_path.iterdir():
            if especialidad_dir.is_dir() and not especialidad_dir.name.startswith('.'):
                specialty = especialidad_dir.name
                print(f"\n📚 Indexando {specialty}...")
                docs = await self.index_especialidad(specialty)
                resultados[specialty] = docs
                print(f"✓ {specialty}: {len(docs)} documentos")

        return resultados

    async def reindex_document(self, documento_id: str):
        """
        Re-indexa un documento específico.

        Args:
            documento_id: ID del documento en MongoDB
        """
        doc = await DocumentoRAG.get(documento_id)
        if not doc:
            raise ValueError(f"Documento no encontrado: {documento_id}")

        # Eliminar chunks antiguos de ChromaDB
        collection_name = doc.specialty.lower()
        for chunk_id in doc.chunk_ids:
            vector_store.delete_document(collection_name, chunk_id)

        # Re-indexar
        file_path = Path(doc.file_path)
        await self.index_document(file_path, doc.specialty)


# Instancia global del indexer
indexer = DocumentIndexer()


# CLI para indexación
if __name__ == "__main__":
    import asyncio
    import sys
    from motor.motor_asyncio import AsyncIOMotorClient
    from app.models.database import init_db
    from app.config.settings import settings

    async def main():
        # Initialize MongoDB connection
        client = AsyncIOMotorClient(settings.mongodb_url)
        database = client[settings.mongodb_db_name]

        # Initialize Beanie ODM
        await init_db(database)

        if len(sys.argv) > 1:
            if sys.argv[1] == "--all":
                print("🚀 Indexando todos los documentos...")
                await indexer.index_all()
            elif sys.argv[1] == "--specialty" and len(sys.argv) > 2:
                specialty = sys.argv[2]
                print(f"🚀 Indexando {specialty}...")
                await indexer.index_especialidad(specialty)
            else:
                print("Uso: python indexer.py [--all | --specialty NOMBRE]")
        else:
            print("Uso: python indexer.py [--all | --specialty NOMBRE]")

        # Close connection
        client.close()

    asyncio.run(main())
