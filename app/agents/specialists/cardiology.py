"""
Cardiology specialist agent.
"""
from app.agents.specialists.base import SpecialistAgent


class CardiologiaAgent(SpecialistAgent):
    """Cardiology specialist agent"""

    def __init__(self):
        """Initialize cardiology agent"""
        super().__init__(specialty="cardiology")


# Global instance
cardiology_agent = CardiologiaAgent()
