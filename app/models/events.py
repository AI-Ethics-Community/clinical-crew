"""
Modelos de eventos para streaming en tiempo real.
"""
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


class BaseStreamEvent(BaseModel):
    """Evento base para streaming"""
    event_type: str = Field(..., description="Tipo de evento")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    consulta_id: str = Field(..., description="ID de la consulta")
    data: Dict[str, Any] = Field(default_factory=dict, description="Datos del evento")


class GPInterrogatingEvent(BaseStreamEvent):
    """GP está generando preguntas de interrogación"""
    event_type: Literal["gp_interrogating"] = "gp_interrogating"


class GPQuestionEvent(BaseStreamEvent):
    """Nueva pregunta del GP"""
    event_type: Literal["gp_question"] = "gp_question"


class GPEvaluatingEvent(BaseStreamEvent):
    """GP está evaluando la consulta"""
    event_type: Literal["gp_evaluating"] = "gp_evaluating"


class InterconsultationCreatedEvent(BaseStreamEvent):
    """Interconsulta creada"""
    event_type: Literal["interconsultation_created"] = "interconsultation_created"


class SpecialistStartedEvent(BaseStreamEvent):
    """Especialista comenzó evaluación"""
    event_type: Literal["specialist_started"] = "specialist_started"


class ToolStartedEvent(BaseStreamEvent):
    """Herramienta iniciada (RAG/PubMed)"""
    event_type: Literal["tool_started"] = "tool_started"


class ToolCompletedEvent(BaseStreamEvent):
    """Herramienta completada"""
    event_type: Literal["tool_completed"] = "tool_completed"


class SourceFoundEvent(BaseStreamEvent):
    """Nueva fuente científica encontrada"""
    event_type: Literal["source_found"] = "source_found"


class SpecialistCompletedEvent(BaseStreamEvent):
    """Especialista terminó evaluación"""
    event_type: Literal["specialist_completed"] = "specialist_completed"


class IntegratingEvent(BaseStreamEvent):
    """Integrando respuestas finales"""
    event_type: Literal["integrating"] = "integrating"


class CompletedEvent(BaseStreamEvent):
    """Consulta completada"""
    event_type: Literal["completed"] = "completed"


class ErrorEvent(BaseStreamEvent):
    """Error en el proceso"""
    event_type: Literal["error"] = "error"


# Union type de todos los eventos
StreamEvent = (
    GPInterrogatingEvent
    | GPQuestionEvent
    | GPEvaluatingEvent
    | InterconsultationCreatedEvent
    | SpecialistStartedEvent
    | ToolStartedEvent
    | ToolCompletedEvent
    | SourceFoundEvent
    | SpecialistCompletedEvent
    | IntegratingEvent
    | CompletedEvent
    | ErrorEvent
)
