"""
General triage agent - handles cases where specialty is unclear or multiple specialties needed.
"""

import logging
from typing import List
from src.agents.base_agent import BaseAgent
from src.core.models import SymptomExtraction, RoutingDecision
from src.core.enums import EscalationLevel

logger = logging.getLogger(__name__)


class GeneralTriageAgent(BaseAgent):
    """General triage agent for unspecialized or complex cases."""

    def __init__(self):
        super().__init__("General Triage")

    def generate_questions(
        self,
        symptoms: SymptomExtraction,
        routing: RoutingDecision,
    ) -> List[str]:
        """
        Generate general triage follow-up questions.
        Focus on understanding severity, impact, and rule out emergencies.
        """
        questions = []
        
        # Always ask about symptom impact
        questions.append(
            "How are these symptoms affecting your daily activities? "
            "Are you able to work, eat, or sleep normally?"
        )
        
        # Ask about recent changes
        questions.append(
            "Have there been any recent changes in your health, diet, stress level, or environment? "
            "Any new medications or supplements?"
        )
        
        # Ask about other symptoms
        if len(questions) < 3:
            questions.append(
                "Are you experiencing any other symptoms like fever, fatigue, or weight changes?"
            )
        
        return questions[:3]

    def generate_recommendations(
        self,
        symptoms: SymptomExtraction,
        routing: RoutingDecision,
    ) -> str:
        """Generate general triage recommendations."""
        
        if routing.escalation_level == EscalationLevel.ER:
            return (
                "Seek immediate emergency care (911). "
                "Based on your symptoms, you need urgent evaluation. "
                "Do not wait. Call 911 or go to the nearest emergency room."
            )
        
        elif routing.escalation_level == EscalationLevel.URGENT_OFFICE:
            return (
                "See your primary care physician urgently (within 24 hours) or visit urgent care. "
                "Your symptoms require prompt evaluation. "
                "If symptoms worsen significantly before your appointment, seek ER care."
            )
        
        elif routing.escalation_level == EscalationLevel.OFFICE:
            return (
                "Schedule an appointment with your primary care physician within 1-2 weeks. "
                "Your symptoms warrant evaluation by a healthcare provider. "
                "In the meantime, monitor your symptoms and note any patterns or triggers. "
                "Rest, stay hydrated, and use over-the-counter remedies as appropriate for symptom relief."
            )
        
        else:  # MONITOR_HOME
            return (
                "Monitor your symptoms at home. "
                "Most acute illnesses resolve on their own within 1-2 weeks. "
                "Get adequate rest, stay hydrated, and maintain good hygiene. "
                "Contact a healthcare provider if symptoms persist beyond 2 weeks, "
                "worsen significantly, or you develop new concerning symptoms."
            )


class MockGeneralTriageAgent(BaseAgent):
    """Mock general triage agent for testing."""

    def __init__(self):
        super().__init__("General Triage")

    def generate_questions(self, symptoms: SymptomExtraction, routing: RoutingDecision) -> List[str]:
        """Return mock triage questions."""
        return [
            "How are these symptoms affecting your daily life?",
            "Have there been any recent changes in your environment or stress?",
            "Are there any other symptoms you're experiencing?",
        ]

    def generate_recommendations(self, symptoms: SymptomExtraction, routing: RoutingDecision) -> str:
        """Return mock triage recommendations."""
        return "See your primary care doctor for proper evaluation and diagnosis."
