"""
Database models with Beanie (MongoDB ODM).
"""
from datetime import datetime
from typing import Dict, List, Optional, Any
from beanie import Document, Indexed
from pydantic import Field

from app.models.consultation import (
    PatientContext,
    GeneralEvaluation,
    InterconsultationNote,
    CounterReferralNote,
    ClinicalRecord,
    InterrogationQuestion,
)


class MedicalConsultation(Document):
    """
    Main medical consultation document in MongoDB.
    """
    user_id: Optional[str] = Field(None, description="User ID")
    original_consultation: str = Field(..., description="Original medical consultation")
    patient_context: PatientContext = Field(..., description="Patient context")

    status: Indexed(str) = Field(  # type: ignore
        default="interrogating",
        description="Current status: interrogating, evaluating, interconsulting, waiting_info, completed, error"
    )

    interrogation_questions: List[InterrogationQuestion] = Field(
        default_factory=list,
        description="GP interrogation questions"
    )

    user_responses: Optional[Dict[str, Any]] = Field(
        None,
        description="User responses to interrogation"
    )

    interrogation_completed: bool = Field(
        default=False,
        description="Whether interrogation phase is complete"
    )

    general_evaluation: Optional[GeneralEvaluation] = Field(
        None,
        description="General practitioner evaluation"
    )

    interconsultations: List[InterconsultationNote] = Field(
        default_factory=list,
        description="Generated interconsultation notes"
    )

    counter_referrals: List[CounterReferralNote] = Field(
        default_factory=list,
        description="Specialist responses"
    )

    pending_questions: List[str] = Field(
        default_factory=list,
        description="Questions requiring user response"
    )

    additional_information: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional information provided by user"
    )

    clinical_record: Optional[ClinicalRecord] = Field(
        None,
        description="Complete clinical record"
    )

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = Field(None, description="Completion date")

    error_message: Optional[str] = Field(None, description="Error message if applicable")
    execution_trace: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Execution trace for debugging"
    )

    class Settings:
        name = "medical_consultations"
        indexes = [
            "user_id",
            "status",
            "created_at",
        ]

    def add_trace(self, step: str, data: Any):
        """Add step to execution trace"""
        self.execution_trace.append({
            "timestamp": datetime.utcnow(),
            "step": step,
            "data": data
        })

    def update_status(self, new_status: str):
        """Update consultation status"""
        self.status = new_status
        self.updated_at = datetime.utcnow()
        if new_status == "completed":
            self.completed_at = datetime.utcnow()

    def add_interconsultation(self, interconsultation: InterconsultationNote):
        """Add interconsultation note"""
        self.interconsultations.append(interconsultation)
        self.updated_at = datetime.utcnow()

    def add_counter_referral(self, counter_referral: CounterReferralNote):
        """Add counter-referral note"""
        self.counter_referrals.append(counter_referral)
        self.updated_at = datetime.utcnow()

    def has_pending_questions(self) -> bool:
        """Check if there are pending questions"""
        return len(self.pending_questions) > 0

    def all_counter_referrals_received(self) -> bool:
        """Check if all expected counter-referrals have been received"""
        return len(self.counter_referrals) >= len(self.interconsultations)


class DocumentoRAG(Document):
    """
    Document for tracking RAG indexed documents.
    """
    specialty: Indexed(str) = Field(..., description="Medical specialty")  # type: ignore
    filename: str = Field(..., description="Original filename")
    file_path: str = Field(..., description="File path")
    document_type: str = Field(..., description="Type: guideline, article, manual, etc.")

    titulo: Optional[str] = Field(None, description="Document title")
    autor: Optional[str] = Field(None, description="Author(s)")
    publication_date: Optional[datetime] = Field(None, description="Publication date")
    fuente: Optional[str] = Field(None, description="Source (journal, institution, etc.)")

    document_hash: str = Field(..., description="Content hash for change detection")
    chunk_ids: List[str] = Field(default_factory=list, description="Chunk IDs in ChromaDB")
    total_chunks: int = Field(default=0, description="Total chunks generated")

    indexado: bool = Field(default=False, description="Is indexed in ChromaDB?")
    indexing_date: Optional[datetime] = Field(None, description="Indexing date")

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
    PubMed search cache.
    """
    query: Indexed(str) = Field(..., description="Search query")  # type: ignore
    specialty: Optional[str] = Field(None, description="Related specialty")

    pmids: List[str] = Field(default_factory=list, description="Found PMIDs")
    total_results: int = Field(default=0, description="Total results")

    articulos: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Article details"
    )

    search_date: datetime = Field(default_factory=datetime.utcnow)
    ttl_dias: int = Field(default=7, description="Cache validity in days")

    class Settings:
        name = "cache_pubmed"
        indexes = [
            "query",
            "search_date",
        ]

    def es_valido(self) -> bool:
        """Check if cache is still valid"""
        dias_transcurridos = (datetime.utcnow() - self.search_date).days
        return dias_transcurridos < self.ttl_dias


async def init_db(database):
    """
    Initialize Beanie with models.

    Args:
        database: motor.motor_asyncio.AsyncIOMotorDatabase instance
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
