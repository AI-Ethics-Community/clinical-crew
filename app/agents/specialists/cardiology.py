"""
Cardiology specialist agent.
"""
from app.agents.specialists.base import SpecialistAgent


class CardiologiaAgent(SpecialistAgent):
    """Cardiology specialist agent"""

    def __init__(self, on_tool_start=None, on_tool_complete=None, on_source_found=None):
        """Initialize cardiology agent"""
        super().__init__(
            specialty="cardiology",
            on_tool_start=on_tool_start,
            on_tool_complete=on_tool_complete,
            on_source_found=on_source_found
        )


# Global instance
cardiology_agent = CardiologiaAgent()
