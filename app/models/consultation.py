"""
Pydantic models for medical consultations and workflow.
"""
from datetime import datetime
from typing import Dict, List, Optional, Any, Literal
from pydantic import BaseModel, Field, ConfigDict
from app.models.sources import ScientificSource


class PatientContext(BaseModel):
    """Patient clinical context"""
    age: Optional[int] = Field(None, description="Patient age", ge=0, le=150)
    sex: Optional[str] = Field(None, description="Patient sex")
    diagnoses: List[str] = Field(default_factory=list, description="Known diagnoses")
    current_medications: List[str] = Field(default_factory=list, description="Current medications")
    allergies: List[str] = Field(default_factory=list, description="Known allergies")
    medical_history: Optional[Dict[str, Any]] = Field(None, description="Additional medical history")
    lab_results: Optional[Dict[str, Any]] = Field(None, description="Laboratory results")
    vital_signs: Optional[Dict[str, Any]] = Field(None, description="Recent vital signs")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "age": 45,
                "sex": "male",
                "diagnoses": ["Type 2 Diabetes Mellitus", "Hypertension"],
                "current_medications": ["Metformin 850mg q12h", "Losartan 50mg q24h"],
                "allergies": ["Penicillin"],
                "lab_results": {
                    "glucose": "180 mg/dL",
                    "hba1c": "8.5%",
                    "creatinine": "1.2 mg/dL"
                }
            }
        }
    )


class InterrogationQuestion(BaseModel):
    """GP interrogation question"""
    question_id: str = Field(..., description="Unique question ID")
    question_text: str = Field(..., description="Question text")
    question_type: Literal["open", "numeric", "multiple_choice"] = Field(..., description="Question type")
    priority: int = Field(..., ge=1, le=5, description="Priority (1=most critical, 5=important)")
    context: Optional[str] = Field(None, description="Context for why this question is being asked")
    options: Optional[List[str]] = Field(None, description="Answer options for multiple_choice questions")


class ConsultationCreate(BaseModel):
    """Model for creating a new consultation"""
    consultation: str = Field(..., description="Medical question or clinical case", min_length=10)
    context: PatientContext = Field(..., description="Patient context")
    user_id: Optional[str] = Field(None, description="User ID submitting the consultation")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "consultation": "Patient with decompensated type 2 diabetes. Can I start sertraline for depression?",
                "context": {
                    "age": 45,
                    "sex": "male",
                    "diagnoses": ["Type 2 Diabetes Mellitus"],
                    "current_medications": ["Metformin 850mg q12h"],
                    "allergies": []
                }
            }
        }
    )


class AdditionalInformation(BaseModel):
    """Additional information provided by user"""
    additional_information: Dict[str, Any] = Field(..., description="Additional requested data")


class GeneralEvaluation(BaseModel):
    """General practitioner evaluation"""
    can_answer_directly: bool = Field(..., description="Can answer directly without specialists")
    required_specialists: List[str] = Field(default_factory=list, description="Specialists to consult")
    reasoning: str = Field(..., description="Decision reasoning")
    estimated_complexity: float = Field(..., description="Case complexity (0-1)", ge=0.0, le=1.0)


class InterconsultationNote(BaseModel):
    """Interconsultation note to a specialist"""
    id: str = Field(..., description="Unique interconsultation ID")
    specialty: str = Field(..., description="Specialty being consulted")
    specific_question: str = Field(..., description="Specific question for the specialist")
    relevant_context: Dict[str, Any] = Field(..., description="Relevant context for the specialist")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class CounterReferralNote(BaseModel):
    """Counter-referral note from a specialist"""
    interconsultation_id: str = Field(..., description="ID of the interconsultation being responded to")
    specialty: str = Field(..., description="Specialty responding")
    evaluation: str = Field(..., description="Case evaluation")
    evidence_used: List[str] = Field(default_factory=list, description="References and evidence consulted")
    clinical_reasoning: str = Field(..., description="Clinical reasoning process")
    response: str = Field(..., description="Response to the question posed")
    recommendations: List[str] = Field(default_factory=list, description="Specific recommendations")
    evidence_level: str = Field(..., description="Evidence level of the response")
    confidence_level: str = Field(default="medium", description="Confidence level: high, medium, low")
    information_limitations: List[str] = Field(default_factory=list, description="Information limitations")
    requires_additional_info: bool = Field(default=False, description="Whether additional information is required")
    additional_questions: List[str] = Field(default_factory=list, description="Additional questions if more info needed")
    sources: List[ScientificSource] = Field(default_factory=list, description="Scientific sources used")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ClinicalRecord(BaseModel):
    """Complete clinical record"""
    general_summary: str = Field(..., description="General practitioner summary")
    complete_notes: str = Field(..., description="All formatted notes")
    final_response: str = Field(..., description="Final integrated response")
    management_plan: Optional[List[str]] = Field(None, description="Suggested management plan")
    recommended_followup: Optional[str] = Field(None, description="Follow-up recommendations")
    all_sources: List[ScientificSource] = Field(default_factory=list, description="All scientific sources used")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ConsultationStatus(str):
    """Possible consultation states"""
    INTERROGATING = "interrogating"
    EVALUATING = "evaluating"
    INTERCONSULTING = "interconsulting"
    WAITING_INFO = "waiting_info"
    INTEGRATING = "integrating"
    COMPLETED = "completed"
    ERROR = "error"


class ConsultationResponse(BaseModel):
    """Consultation response"""
    consultation_id: str = Field(..., description="Consultation ID")
    status: str = Field(..., description="Current consultation status")
    message: Optional[str] = Field(None, description="Descriptive message")
    clinical_record: Optional[ClinicalRecord] = Field(None, description="Complete record when ready")
    progress: Optional[Dict[str, Any]] = Field(None, description="Progress information")


class CompleteConsultation(BaseModel):
    """Complete consultation with all details"""
    consultation_id: str
    user_id: Optional[str]
    original_consultation: str
    patient_context: PatientContext
    status: str
    timestamp: datetime
    interrogation_questions: List[InterrogationQuestion] = Field(default_factory=list)
    interrogation_completed: bool = False
    general_evaluation: Optional[GeneralEvaluation]
    interconsultations: List[InterconsultationNote]
    counter_referrals: List[CounterReferralNote]
    clinical_record: Optional[ClinicalRecord]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
