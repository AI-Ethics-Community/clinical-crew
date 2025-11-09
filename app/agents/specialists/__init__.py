"""
Medical specialist agents.
"""
from app.agents.specialists.base import SpecialistAgent
from app.agents.specialists.cardiology import CardiologiaAgent, cardiology_agent
from app.agents.specialists.endocrinology import EndocrinologiaAgent, endocrinology_agent
from app.agents.specialists.pharmacology import FarmacologiaAgent, pharmacology_agent

# Map specialty names to agent instances (support both Spanish and English)
SPECIALIST_AGENTS = {
    # Spanish names
    "cardiologia": cardiology_agent,
    "cardiología": cardiology_agent,
    "endocrinologia": endocrinology_agent,
    "endocrinología": endocrinology_agent,
    "farmacologia": pharmacology_agent,
    "farmacología": pharmacology_agent,
    # English names
    "cardiology": cardiology_agent,
    "endocrinology": endocrinology_agent,
    "pharmacology": pharmacology_agent,
}


def get_specialist_agent(specialty: str) -> SpecialistAgent:
    """
    Get specialist agent by specialty name.

    Args:
        specialty: Specialty name (e.g., "cardiologia" or "cardiology")

    Returns:
        Specialist agent instance

    Raises:
        ValueError: If specialty not found
    """
    specialty_lower = specialty.lower()

    if specialty_lower not in SPECIALIST_AGENTS:
        raise ValueError(f"Specialist not found: {specialty}")

    return SPECIALIST_AGENTS[specialty_lower]


__all__ = [
    "SpecialistAgent",
    "CardiologiaAgent",
    "EndocrinologiaAgent",
    "FarmacologiaAgent",
    "cardiology_agent",
    "endocrinology_agent",
    "pharmacology_agent",
    "SPECIALIST_AGENTS",
    "get_specialist_agent",
]
