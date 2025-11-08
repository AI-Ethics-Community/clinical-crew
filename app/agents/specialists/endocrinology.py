"""
Endocrinology specialist agent.
"""
from app.agents.specialists.base import SpecialistAgent


class EndocrinologiaAgent(SpecialistAgent):
    """Endocrinology specialist agent"""

    def __init__(self):
        """Initialize endocrinology agent"""
        super().__init__(specialty="endocrinology")


# Global instance
endocrinology_agent = EndocrinologiaAgent()
