"""
Cardiology specialist agent - handles chest pain and cardiac symptoms.
"""

import logging
from typing import List
from app.agents.base_agent import BaseAgent
from app.core.models import SymptomExtraction, RoutingDecision
from app.core.enums import EscalationLevel

logger = logging.getLogger(__name__)


class CardiologyAgent(BaseAgent):
    """Cardiology specialist agent for cardiac assessment."""

    def __init__(self):
        super().__init__("Cardiology")

    def generate_questions(
        self,
        symptoms: SymptomExtraction,
        routing: RoutingDecision,
    ) -> List[str]:
        """
        Generate cardiology-specific follow-up questions.
        
        Question selection based on presenting symptoms and severity.
        """
        questions = []
        symptom_text = " ".join(symptoms.symptoms).lower()
        
        # Always ask about chest pain characteristics if mentioned
        if "chest" in symptom_text or "heart" in symptom_text:
            questions.append(
                "On a scale of 1-10, how severe is your chest pain or discomfort? "
                "Is it constant or intermittent?"
            )
        
        # Ask about associated symptoms
        if any(x in symptom_text for x in ["breath", "shortness", "dyspnea"]):
            questions.append(
                "Are you having difficulty breathing at rest or only with exertion? "
                "When did this start?"
            )
        
        # Ask about risk factors
        if symptoms.severity in ["high", "critical"]:
            questions.append(
                "Do you have a history of high blood pressure, diabetes, or high cholesterol? "
                "Do you smoke or have a family history of heart disease?"
            )
        
        # Ask about exertional component
        if len(questions) < 3:
            questions.append(
                "Did the pain start during physical activity, at rest, or after a meal?"
            )
        
        # Ensure 2-3 questions
        return questions[:3]

    def generate_recommendations(
        self,
        symptoms: SymptomExtraction,
        routing: RoutingDecision,
    ) -> str:
        """Generate cardiology recommendations based on severity and presentation."""
        
        if routing.escalation_level == EscalationLevel.ER:
            return (
                "URGENT - Seek immediate emergency care (911). "
                "You may be experiencing acute coronary syndrome or another life-threatening condition. "
                "Do not drive yourself. Call 911 immediately."
            )
        
        elif routing.escalation_level == EscalationLevel.URGENT_OFFICE:
            return (
                "Schedule an urgent cardiology appointment within 24 hours. "
                "Your symptoms require prompt evaluation including ECG and troponin testing. "
                "Avoid strenuous activity until evaluated. "
                "If symptoms worsen, go to the nearest ER."
            )
        
        elif routing.escalation_level == EscalationLevel.OFFICE:
            return (
                "Schedule a cardiology appointment within 1-2 weeks. "
                "Your symptoms warrant evaluation by a cardiologist. "
                "Keep track of when symptoms occur and what triggers them. "
                "Avoid known triggers until evaluated."
            )
        
        else:  # MONITOR_HOME
            return (
                "Monitor your symptoms at home. "
                "Keep a log of chest discomfort episodes, triggers, and duration. "
                "Consider lifestyle modifications: reduce stress, increase physical activity gradually, "
                "maintain healthy diet. "
                "Contact a cardiologist if symptoms increase or new symptoms develop."
            )


class MockCardiologyAgent(BaseAgent):
    """Mock cardiology agent for testing."""

    def __init__(self):
        super().__init__("Cardiology")

    def generate_questions(self, symptoms: SymptomExtraction, routing: RoutingDecision) -> List[str]:
        """Return mock cardiology questions."""
        return [
            "On a scale of 1-10, how severe is your chest pain?",
            "Do you have a history of heart disease or high blood pressure?",
            "When did the chest pain start and what were you doing?",
        ]

    def generate_recommendations(self, symptoms: SymptomExtraction, routing: RoutingDecision) -> str:
        """Return mock cardiology recommendations."""
        if routing.escalation_level in ["ER", "urgent_office"]:
            return "Seek immediate medical attention. This may be a cardiac emergency."
        return "Schedule a cardiology appointment for proper evaluation."
