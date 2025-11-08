"""
Medical specialist agents.
"""
from app.agents.specialists.base import SpecialistAgent
from app.agents.specialists.cardiology import CardiologiaAgent, cardiology_agent
from app.agents.specialists.endocrinology import EndocrinologiaAgent, endocrinology_agent
from app.agents.specialists.pharmacology import FarmacologiaAgent, pharmacology_agent

# Map specialty names to agent instances
SPECIALIST_AGENTS = {
    "cardiologia": cardiology_agent,
    "endocrinologia": endocrinology_agent,
    "farmacologia": pharmacology_agent,
}


def get_specialist_agent(specialty: str) -> SpecialistAgent:
    """
    Get specialist agent by specialty name.

    Args:
        specialty: Specialty name (e.g., "cardiologia")

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
