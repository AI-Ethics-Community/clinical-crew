"""
Clinical pharmacology specialist agent.
"""
from app.agents.specialists.base import SpecialistAgent


class FarmacologiaAgent(SpecialistAgent):
    """Clinical pharmacology specialist agent"""

    def __init__(self, on_tool_start=None, on_tool_complete=None, on_source_found=None):
        """Initialize pharmacology agent"""
        super().__init__(
            specialty="pharmacology",
            on_tool_start=on_tool_start,
            on_tool_complete=on_tool_complete,
            on_source_found=on_source_found
        )


# Global instance
pharmacology_agent = FarmacologiaAgent()
