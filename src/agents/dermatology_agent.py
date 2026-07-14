"""
Dermatology specialist agent - handles skin conditions, rashes, and lesions.
"""

import logging
from typing import List
from src.agents.base_agent import BaseAgent
from src.core.models import SymptomExtraction, RoutingDecision
from src.core.enums import EscalationLevel

logger = logging.getLogger(__name__)


class DermatologyAgent(BaseAgent):
    """Dermatology specialist agent for skin condition assessment."""

    def __init__(self):
        super().__init__("Dermatology")

    def generate_questions(
        self,
        symptoms: SymptomExtraction,
        routing: RoutingDecision,
    ) -> List[str]:
        """
        Generate dermatology-specific follow-up questions.
        Focus on lesion characteristics, distribution, and associated symptoms.
        """
        questions = []
        symptom_text = " ".join(symptoms.symptoms).lower()
        
        # Always ask about lesion appearance
        questions.append(
            "What does the rash/lesion look like? Is it red, brown, or another color? "
            "Is it flat, raised, or blistering?"
        )
        
        # Ask about distribution and progression
        if any(x in symptom_text for x in ["rash", "lesion", "skin"]):
            questions.append(
                "Is the rash localized to one area or spreading? "
                "Is it itchy, painful, or causing other symptoms?"
            )
        
        # Ask about triggers and history
        if len(questions) < 3:
            questions.append(
                "Have you used any new products, detergents, or been exposed to anything new? "
                "Do you have known allergies or sensitive skin?"
            )
        
        # Ensure 2-3 questions
        return questions[:3]

    def generate_recommendations(
        self,
        symptoms: SymptomExtraction,
        routing: RoutingDecision,
    ) -> str:
        """Generate dermatology recommendations based on condition severity."""
        
        if routing.escalation_level == EscalationLevel.URGENT_OFFICE:
            return (
                "See a dermatologist or call your primary care urgently (within 24 hours). "
                "Your symptoms suggest a possible infection or severe allergic reaction. "
                "Do not scratch or pick at the lesion. "
                "Avoid products and triggers until evaluated. "
                "Seek ER care if you develop fever, difficulty breathing, or facial swelling."
            )
        
        elif routing.escalation_level == EscalationLevel.OFFICE:
            return (
                "Schedule a dermatology appointment within 1-2 weeks. "
                "In the meantime: avoid scratching (can worsen infection), "
                "use mild soap and lukewarm water, apply fragrance-free moisturizer, "
                "avoid known triggers. "
                "Over-the-counter hydrocortisone cream may help with itching. "
                "Keep the area clean and monitor for signs of infection."
            )
        
        else:  # MONITOR_HOME
            return (
                "Monitor the condition at home. "
                "Maintain good skin hygiene with gentle, fragrance-free products. "
                "Avoid scratching. Apply moisturizer to affected area. "
                "Consider allergen triggers and avoid them. "
                "Most mild rashes resolve in 1-2 weeks. "
                "Contact a provider if the rash spreads, worsens, or shows signs of infection."
            )


class MockDermatologyAgent(BaseAgent):
    """Mock dermatology agent for testing."""

    def __init__(self):
        super().__init__("Dermatology")

    def generate_questions(self, symptoms: SymptomExtraction, routing: RoutingDecision) -> List[str]:
        """Return mock dermatology questions."""
        return [
            "What does the rash look like? What color is it?",
            "When did the rash first appear?",
            "Is the rash spreading or staying in one area?",
        ]

    def generate_recommendations(self, symptoms: SymptomExtraction, routing: RoutingDecision) -> str:
        """Return mock dermatology recommendations."""
        return "Keep the area clean and dry. Avoid scratching. Schedule a dermatology appointment if it persists or worsens."
