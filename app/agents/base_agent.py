"""
Base agent class for all specialty-specific agents.
Provides common functionality for question generation and recommendation logic.
"""

import logging
from abc import ABC, abstractmethod
from typing import List, Optional
from app.core.models import SymptomExtraction, RoutingDecision

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """Abstract base agent for specialty-specific response generation."""

    def __init__(self, specialty_name: str):
        """Initialize agent with specialty name."""
        self.specialty_name = specialty_name

    @abstractmethod
    def generate_questions(
        self,
        symptoms: SymptomExtraction,
        routing: RoutingDecision,
    ) -> List[str]:
        """
        Generate follow-up questions for this specialty.
        
        Args:
            symptoms: Extracted symptom data
            routing: Routing decision
            
        Returns:
            List of 2-4 follow-up questions
        """
        pass

    @abstractmethod
    def generate_recommendations(
        self,
        symptoms: SymptomExtraction,
        routing: RoutingDecision,
    ) -> str:
        """
        Generate clinical recommendations.
        
        Args:
            symptoms: Extracted symptom data
            routing: Routing decision
            
        Returns:
            Recommendation text
        """
        pass

    def get_assessment(
        self,
        symptoms: SymptomExtraction,
        routing: RoutingDecision,
    ) -> tuple[List[str], str]:
        """
        Get both questions and recommendations.
        
        Returns:
            (questions, recommendations)
        """
        questions = self.generate_questions(symptoms, routing)
        recommendations = self.generate_recommendations(symptoms, routing)
        return questions, recommendations

    def _filter_symptoms_by_keywords(
        self,
        symptoms: List[str],
        keywords: List[str]
    ) -> List[str]:
        """Filter symptoms that match any keyword."""
        result = []
        symptom_text = " ".join(symptoms).lower()
        
        for kw in keywords:
            if kw in symptom_text:
                result.append(kw)
        
        return result

    def _has_any_symptom(self, symptoms: List[str], keywords: List[str]) -> bool:
        """Check if any keyword appears in symptoms."""
        symptom_text = " ".join(symptoms).lower()
        return any(kw in symptom_text for kw in keywords)
