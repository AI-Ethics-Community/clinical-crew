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


def get_specialist_agent(
    specialty: str,
    on_tool_start=None,
    on_tool_complete=None,
    on_source_found=None
) -> SpecialistAgent:
    """
    Get specialist agent by specialty name.

    Args:
        specialty: Specialty name (e.g., "cardiologia" or "cardiology")
        on_tool_start: Optional callback when a tool starts
        on_tool_complete: Optional callback when a tool completes
        on_source_found: Optional callback when a source is found

    Returns:
        Specialist agent instance

    Raises:
        ValueError: If specialty not found
    """
    specialty_lower = specialty.lower()

    # Map both Spanish and English names to canonical English names
    specialty_map = {
        "cardiologia": "cardiology",
        "cardiología": "cardiology",
        "cardiology": "cardiology",
        "endocrinologia": "endocrinology",
        "endocrinología": "endocrinology",
        "endocrinology": "endocrinology",
        "farmacologia": "pharmacology",
        "farmacología": "pharmacology",
        "pharmacology": "pharmacology",
    }

    if specialty_lower not in specialty_map:
        raise ValueError(f"Specialist not found: {specialty}")

    canonical_specialty = specialty_map[specialty_lower]

    # Create new instance with callbacks
    if canonical_specialty == "cardiology":
        return CardiologiaAgent(on_tool_start, on_tool_complete, on_source_found)
    elif canonical_specialty == "endocrinology":
        return EndocrinologiaAgent(on_tool_start, on_tool_complete, on_source_found)
    elif canonical_specialty == "pharmacology":
        return FarmacologiaAgent(on_tool_start, on_tool_complete, on_source_found)
    else:
        raise ValueError(f"Specialist not found: {specialty}")


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
