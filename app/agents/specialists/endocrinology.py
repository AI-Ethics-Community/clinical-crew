"""
Endocrinology specialist agent.
"""
from app.agents.specialists.base import SpecialistAgent


class EndocrinologiaAgent(SpecialistAgent):
    """Endocrinology specialist agent"""

    def __init__(self, on_tool_start=None, on_tool_complete=None, on_source_found=None):
        """Initialize endocrinology agent"""
        super().__init__(
            specialty="endocrinology",
            on_tool_start=on_tool_start,
            on_tool_complete=on_tool_complete,
            on_source_found=on_source_found
        )


# Global instance
endocrinology_agent = EndocrinologiaAgent()
