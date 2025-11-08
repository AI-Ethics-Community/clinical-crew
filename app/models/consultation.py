"""
Modelos Pydantic para consultations médicas y flujo de trabajo.
"""
from datetime import datetime
from typing import Dict, List, Optional, Any, Literal
from pydantic import BaseModel, Field, ConfigDict


class PatientContext(BaseModel):
    """Contexto clínico del paciente"""
    edad: Optional[int] = Field(None, description="Edad del paciente", ge=0, le=150)
    sexo: Optional[str] = Field(None, description="Sexo del paciente")
    diagnosticos: List[str] = Field(default_factory=list, description="Diagnósticos conocidos")
    medicamentos_actuales: List[str] = Field(default_factory=list, description="Medicamentos que toma")
    alergias: List[str] = Field(default_factory=list, description="Alergias conocidas")
    antecedentes: Optional[Dict[str, Any]] = Field(None, description="Antecedentes médicos adicionales")
    laboratorios: Optional[Dict[str, Any]] = Field(None, description="Resultados de laboratorio")
    signos_vitales: Optional[Dict[str, Any]] = Field(None, description="Signos vitales recientes")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "edad": 45,
                "sexo": "masculino",
                "diagnosticos": ["Diabetes Mellitus tipo 2", "Hipertensión arterial"],
                "medicamentos_actuales": ["Metformina 850mg c/12h", "Losartán 50mg c/24h"],
                "alergias": ["Penicilina"],
                "laboratorios": {
                    "glucosa": "180 mg/dL",
                    "hba1c": "8.5%",
                    "creatinina": "1.2 mg/dL"
                }
            }
        }
    )


class ConsultaCreate(BaseModel):
    """Modelo para crear una nueva consultation"""
    consultation: str = Field(..., description="Pregunta o caso clínico del médico", min_length=10)
    contexto: PatientContext = Field(..., description="Contexto del paciente")
    usuario_id: Optional[str] = Field(None, description="ID del usuario que realiza la consultation")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "consultation": "Paciente con diabetes tipo 2 descompensada. ¿Puedo iniciar sertralina para depresión?",
                "contexto": {
                    "edad": 45,
                    "sexo": "masculino",
                    "diagnosticos": ["Diabetes Mellitus tipo 2"],
                    "medicamentos_actuales": ["Metformina 850mg c/12h"],
                    "alergias": []
                }
            }
        }
    )


class InformacionAdicional(BaseModel):
    """Información adicional proporcionada por el usuario"""
    additional_information: Dict[str, Any] = Field(..., description="Datos adicionales solicitados")


class EvaluacionGeneral(BaseModel):
    """Evaluación del médico general"""
    can_answer_directly: bool = Field(..., description="¿Puede responder directamente?")
    required_specialists: List[str] = Field(default_factory=list, description="Especialistas a interconsultar")
    razonamiento: str = Field(..., description="Razonamiento de la decisión")
    estimated_complexity: float = Field(..., description="Complejidad del caso (0-1)", ge=0.0, le=1.0)


class InterconsultationNote(BaseModel):
    """Nota de interconsultation a un especialista"""
    id: str = Field(..., description="ID único de la interconsultation")
    specialty: str = Field(..., description="Especialidad consultada")
    specific_question: str = Field(..., description="Pregunta específica para el especialista")
    relevant_context: Dict[str, Any] = Field(..., description="Contexto relevante para el especialista")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class CounterReferralNote(BaseModel):
    """Nota de counter_referral de un especialista"""
    interconsulta_id: str = Field(..., description="ID de la interconsultation respondida")
    specialty: str = Field(..., description="Especialidad que responde")
    evaluacion: str = Field(..., description="Evaluación del caso")
    evidence_used: List[str] = Field(default_factory=list, description="Referencias y evidencia consultada")
    clinical_reasoning: str = Field(..., description="Proceso de razonamiento clínico")
    respuesta: str = Field(..., description="Respuesta a la pregunta planteada")
    recomendaciones: List[str] = Field(default_factory=list, description="Recomendaciones específicas")
    evidence_level: str = Field(..., description="Nivel de evidencia de la respuesta")
    requires_additional_info: bool = Field(default=False, description="¿Requiere más información?")
    additional_questions: List[str] = Field(default_factory=list, description="Preguntas al usuario")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ClinicalRecord(BaseModel):
    """Expediente clínico completo"""
    general_summary: str = Field(..., description="Resumen del médico general")
    complete_notes: str = Field(..., description="Todas las notes formateadas")
    final_response: str = Field(..., description="Respuesta integrada final")
    management_plan: Optional[List[str]] = Field(None, description="Plan de manejo sugerido")
    recommended_followup: Optional[str] = Field(None, description="Recomendaciones de seguimiento")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class EstadoConsulta(str):
    """Estados posibles de una consultation"""
    EVALUANDO = "evaluando"
    INTERCONSULTANDO = "interconsultando"
    ESPERANDO_INFO = "esperando_info"
    INTEGRANDO = "integrando"
    COMPLETADO = "completado"
    ERROR = "error"


class ConsultaResponse(BaseModel):
    """Respuesta de una consultation"""
    consulta_id: str = Field(..., description="ID de la consultation")
    estado: str = Field(..., description="Estado actual de la consultation")
    mensaje: Optional[str] = Field(None, description="Mensaje descriptivo")
    clinical_record: Optional[ClinicalRecord] = Field(None, description="Expediente completo (cuando está listo)")
    progreso: Optional[Dict[str, Any]] = Field(None, description="Información de progreso")


class ConsultaCompleta(BaseModel):
    """Consulta completa con todos los detalles"""
    consulta_id: str
    usuario_id: Optional[str]
    original_consultation: str
    patient_context: PatientContext
    estado: str
    timestamp: datetime

    # Flujo de trabajo
    general_evaluation: Optional[EvaluacionGeneral]
    interconsultations: List[InterconsultationNote]
    counter_referrals: List[CounterReferralNote]
    clinical_record: Optional[ClinicalRecord]

    # Metadata
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
