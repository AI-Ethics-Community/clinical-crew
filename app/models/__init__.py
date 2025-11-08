"""
Data models for the application.
"""
from app.models.consultation import (
    PatientContext,
    ConsultaCreate as ConsultationCreate,
    InformacionAdicional as AdditionalInformation,
    EvaluacionGeneral as GeneralEvaluation,
    InterconsultationNote,
    CounterReferralNote,
    ClinicalRecord,
    EstadoConsulta as ConsultationStatus,
    ConsultaResponse as ConsultationResponse,
    ConsultaCompleta as CompleteConsultation,
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
]
