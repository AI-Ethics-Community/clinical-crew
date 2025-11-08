"""
Clinical pharmacology specialist agent.
"""
from app.agents.specialists.base import SpecialistAgent


class FarmacologiaAgent(SpecialistAgent):
    """Clinical pharmacology specialist agent"""

    def __init__(self):
        """Initialize pharmacology agent"""
        super().__init__(specialty="pharmacology")


# Global instance
pharmacology_agent = FarmacologiaAgent()
