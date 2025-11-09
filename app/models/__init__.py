"""
Data models for the application.
"""
from app.models.consultation import (
    PatientContext,
    ConsultationCreate,
    AdditionalInformation,
    GeneralEvaluation,
    InterconsultationNote,
    CounterReferralNote,
    ClinicalRecord,
    ConsultationStatus,
    ConsultationResponse,
    CompleteConsultation,
    InterrogationQuestion,
)

from app.models.notes import (
    PlantillaNotaInterconsulta as InterconsultationNoteTemplate,
    PlantillaNotaContrarreferencia as CounterReferralNoteTemplate,
    PlantillaExpedienteClinico as ClinicalRecordTemplate,
    FormatoContextoPaciente as PatientContextFormatter,
)

from app.models.database import (
    MedicalConsultation,
    DocumentoRAG,
    BusquedaPubMed,
    init_db,
)

from app.models.sources import (
    ScientificSource,
    SourceType,
)

from app.models.events import (
    BaseStreamEvent,
    GPInterrogatingEvent,
    GPQuestionEvent,
    GPEvaluatingEvent,
    InterconsultationCreatedEvent,
    SpecialistStartedEvent,
    ToolStartedEvent,
    ToolCompletedEvent,
    SourceFoundEvent,
    SpecialistCompletedEvent,
    IntegratingEvent,
    CompletedEvent,
    ErrorEvent,
    StreamEvent,
)

__all__ = [
    # Consultation
    "PatientContext",
    "ConsultationCreate",
    "AdditionalInformation",
    "GeneralEvaluation",
    "InterconsultationNote",
    "CounterReferralNote",
    "ClinicalRecord",
    "ConsultationStatus",
    "ConsultationResponse",
    "CompleteConsultation",
    "InterrogationQuestion",
    # Notes
    "InterconsultationNoteTemplate",
    "CounterReferralNoteTemplate",
    "ClinicalRecordTemplate",
    "PatientContextFormatter",
    # Database
    "MedicalConsultation",
    "DocumentoRAG",
    "BusquedaPubMed",
    "init_db",
    # Sources
    "ScientificSource",
    "SourceType",
    # Events
    "BaseStreamEvent",
    "GPInterrogatingEvent",
    "GPQuestionEvent",
    "GPEvaluatingEvent",
    "InterconsultationCreatedEvent",
    "SpecialistStartedEvent",
    "ToolStartedEvent",
    "ToolCompletedEvent",
    "SourceFoundEvent",
    "SpecialistCompletedEvent",
    "IntegratingEvent",
    "CompletedEvent",
    "ErrorEvent",
    "StreamEvent",
]
