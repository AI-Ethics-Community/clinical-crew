"""
Multi-agent system for medical consultations.
"""
from app.agents.general_practitioner import GeneralPractitionerAgent, general_practitioner
from app.agents.specialists import (
    SpecialistAgent,
    get_specialist_agent,
    SPECIALIST_AGENTS
)
from app.agents.graph import (
    medical_consultation_workflow,
    MedicalConsultationState,
    create_workflow
)

# Alias for backwards compatibility with tests
GeneralPractitioner = GeneralPractitionerAgent

__all__ = [
    "GeneralPractitionerAgent",
    "GeneralPractitioner",
    "general_practitioner",
    "SpecialistAgent",
    "get_specialist_agent",
    "SPECIALIST_AGENTS",
    "medical_consultation_workflow",
    "MedicalConsultationState",
    "create_workflow",
]
