"""
Agent factory - creates appropriate agent instance based on specialty.
"""

import logging
from app.core.enums import Specialty
from app.agents.base_agent import BaseAgent
from app.agents.cardiology_agent import CardiologyAgent, MockCardiologyAgent
from app.agents.orthopedics_agent import OrthopedicsAgent, MockOrthopedicsAgent
from app.agents.dermatology_agent import DermatologyAgent, MockDermatologyAgent
from app.agents.triage_agent import GeneralTriageAgent, MockGeneralTriageAgent

logger = logging.getLogger(__name__)


class AgentFactory:
    """Factory for creating specialty agents."""

    _agents = {
        Specialty.CARDIOLOGY: CardiologyAgent,
        Specialty.ORTHOPEDICS: OrthopedicsAgent,
        Specialty.DERMATOLOGY: DermatologyAgent,
        Specialty.GENERAL_TRIAGE: GeneralTriageAgent,
    }

    _mock_agents = {
        Specialty.CARDIOLOGY: MockCardiologyAgent,
        Specialty.ORTHOPEDICS: MockOrthopedicsAgent,
        Specialty.DERMATOLOGY: MockDermatologyAgent,
        Specialty.GENERAL_TRIAGE: MockGeneralTriageAgent,
    }

    @classmethod
    def get_agent(cls, specialty: Specialty, use_mock: bool = False) -> BaseAgent:
        """
        Get agent for specialty.
        
        Args:
            specialty: Medical specialty
            use_mock: If True, return mock agent for testing
            
        Returns:
            Agent instance
            
        Raises:
            ValueError: If specialty unknown
        """
        agents = cls._mock_agents if use_mock else cls._agents
        
        if specialty not in agents:
            logger.error(f"Unknown specialty: {specialty}")
            raise ValueError(f"Unknown specialty: {specialty}")
        
        agent_class = agents[specialty]
        return agent_class()

    @classmethod
    def get_all_agents(cls, use_mock: bool = False) -> dict:
        """Get all agents as dictionary."""
        agents = {}
        for specialty in Specialty:
            agents[specialty] = cls.get_agent(specialty, use_mock)
        return agents
