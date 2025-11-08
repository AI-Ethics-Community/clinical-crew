"""
Modelos de base de datos con Beanie (MongoDB ODM).
"""
from datetime import datetime
from typing import Dict, List, Optional, Any
from beanie import Document, Indexed
from pydantic import Field

from app.models.consultation import (
    PatientContext,
    EvaluacionGeneral,
    InterconsultationNote,
    CounterReferralNote,
    ClinicalRecord,
)


class MedicalConsultation(Document):
    """
    Documento principal de consultation médica en MongoDB.
    """

    # Información básica
    usuario_id: Optional[str] = Field(None, description="ID del usuario")
    original_consultation: str = Field(..., description="Consulta original del médico")
    patient_context: PatientContext = Field(..., description="Contexto del paciente")

    # Estado
    estado: Indexed(str) = Field(  # type: ignore
        default="evaluando",
        description="Estado actual: evaluando, interconsultando, esperando_info, completado, error"
    )

    # Flujo de trabajo
    general_evaluation: Optional[EvaluacionGeneral] = Field(
        None,
        description="Evaluación del médico general"
    )

    interconsultations: List[InterconsultationNote] = Field(
        default_factory=list,
        description="Notas de interconsultation generadas"
    )

    counter_referrals: List[CounterReferralNote] = Field(
        default_factory=list,
        description="Respuestas de specialists"
    )

    # Preguntas pendientes
    pending_questions: List[str] = Field(
        default_factory=list,
        description="Preguntas que requieren respuesta del usuario"
    )

    additional_information: Optional[Dict[str, Any]] = Field(
        None,
        description="Información adicional proporcionada por el usuario"
    )

    # Expediente final
    clinical_record: Optional[ClinicalRecord] = Field(
        None,
        description="Expediente clínico completo"
    )

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = Field(None, description="Fecha de completado")

    # Tracking y debugging
    error_message: Optional[str] = Field(None, description="Mensaje de error si aplica")
    execution_trace: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Trace de ejecución para debugging"
    )

    class Settings:
        name = "medical_consultations"
        indexes = [
            "usuario_id",
            "estado",
            "created_at",
        ]

    def add_trace(self, step: str, data: Any):
        """Agrega un paso al trace de ejecución"""
        self.execution_trace.append({
            "timestamp": datetime.utcnow(),
            "step": step,
            "data": data
        })

    def actualizar_estado(self, nuevo_estado: str):
        """Actualiza el estado de la consultation"""
        self.estado = nuevo_estado
        self.updated_at = datetime.utcnow()
        if nuevo_estado == "completado":
            self.completed_at = datetime.utcnow()

    def agregar_interconsulta(self, interconsultation: InterconsultationNote):
        """Agrega una nota de interconsultation"""
        self.interconsultations.append(interconsultation)
        self.updated_at = datetime.utcnow()

    def agregar_contrarreferencia(self, counter_referral: CounterReferralNote):
        """Agrega una nota de counter_referral"""
        self.counter_referrals.append(counter_referral)
        self.updated_at = datetime.utcnow()

    def tiene_preguntas_pendientes(self) -> bool:
        """Verifica si hay preguntas pendientes"""
        return len(self.pending_questions) > 0

    def todas_contrarreferencias_recibidas(self) -> bool:
        """Verifica si se recibieron todas las counter_referrals esperadas"""
        return len(self.counter_referrals) >= len(self.interconsultations)


class DocumentoRAG(Document):
    """
    Documento para tracking de documentos indexados en RAG.
    """

    specialty: Indexed(str) = Field(..., description="Especialidad médica")  # type: ignore
    filename: str = Field(..., description="Nombre del archivo original")
    file_path: str = Field(..., description="Ruta del archivo")
    document_type: str = Field(..., description="Tipo: guia, articulo, manual, etc.")

    # Metadata del documento
    titulo: Optional[str] = Field(None, description="Título del documento")
    autor: Optional[str] = Field(None, description="Autor(es)")
    publication_date: Optional[datetime] = Field(None, description="Fecha de publicación")
    fuente: Optional[str] = Field(None, description="Fuente (journal, institución, etc.)")

    # Indexación
    document_hash: str = Field(..., description="Hash del contenido para detectar cambios")
    chunk_ids: List[str] = Field(default_factory=list, description="IDs de chunks en ChromaDB")
    total_chunks: int = Field(default=0, description="Total de chunks generados")

    # Estado
    indexado: bool = Field(default=False, description="¿Está indexado en ChromaDB?")
    indexing_date: Optional[datetime] = Field(None, description="Fecha de indexación")

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "rag_documents"
        indexes = [
            "specialty",
            "document_type",
            "indexado",
        ]


class BusquedaPubMed(Document):
    """
    Cache de búsquedas en PubMed.
    """

    query: Indexed(str) = Field(..., description="Query de búsqueda")  # type: ignore
    specialty: Optional[str] = Field(None, description="Especialidad relacionada")

    # Resultados
    pmids: List[str] = Field(default_factory=list, description="PMIDs encontrados")
    total_results: int = Field(default=0, description="Total de resultados")

    # Detalles de artículos
    articulos: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Detalles de los artículos"
    )

    # Cache
    search_date: datetime = Field(default_factory=datetime.utcnow)
    ttl_dias: int = Field(default=7, description="Días de validez del cache")

    class Settings:
        name = "cache_pubmed"
        indexes = [
            "query",
            "search_date",
        ]

    def es_valido(self) -> bool:
        """Verifica si el cache aún es válido"""
        dias_transcurridos = (datetime.utcnow() - self.search_date).days
        return dias_transcurridos < self.ttl_dias


# Inicialización de Beanie
async def init_db(database):
    """
    Inicializa Beanie con los modelos.

    Args:
        database: Instancia de motor.motor_asyncio.AsyncIOMotorDatabase
    """
    from beanie import init_beanie

    await init_beanie(
        database=database,
        document_models=[
            MedicalConsultation,
            DocumentoRAG,
            BusquedaPubMed,
        ]
    )
