"""
Orthopedics specialist agent - handles joint injuries, fractures, and bone conditions.
"""

import logging
from typing import List
from app.agents.base_agent import BaseAgent
from app.core.models import SymptomExtraction, RoutingDecision
from app.core.enums import EscalationLevel

logger = logging.getLogger(__name__)


class OrthopedicsAgent(BaseAgent):
    """Orthopedics specialist agent for musculoskeletal assessment."""

    def __init__(self):
        super().__init__("Orthopedics")

    def generate_questions(
        self,
        symptoms: SymptomExtraction,
        routing: RoutingDecision,
    ) -> List[str]:
        """
        Generate orthopedics-specific follow-up questions.
        Focus on mechanism of injury, range of motion, and functional impairment.
        """
        questions = []
        symptom_text = " ".join(symptoms.symptoms).lower()
        
        # Ask about mechanism of injury
        questions.append(
            "Can you describe exactly how the injury occurred? "
            "Was there a fall, twist, or direct impact?"
        )
        
        # Ask about swelling and range of motion
        if any(x in symptom_text for x in ["swelling", "swollen", "pain", "joint"]):
            questions.append(
                "Is there visible swelling? Can you move the joint, or is it restricted? "
                "Can you put weight on it?"
            )
        
        # Ask about associated symptoms
        if len(questions) < 3:
            questions.append(
                "Do you have numbness, tingling, or color changes in the affected area? "
                "Is the skin warm or cold?"
            )
        
        # Ensure 2-3 questions
        return questions[:3]

    def generate_recommendations(
        self,
        symptoms: SymptomExtraction,
        routing: RoutingDecision,
    ) -> str:
        """Generate orthopedics recommendations based on injury severity."""
        
        if routing.escalation_level == EscalationLevel.ER:
            return (
                "Seek immediate emergency care (911). "
                "You may have a severe fracture, open fracture, or vascular injury. "
                "Do not attempt to move or test the joint. "
                "Immobilize the affected limb and call 911."
            )
        
        elif routing.escalation_level == EscalationLevel.URGENT_OFFICE:
            return (
                "See an orthopedic specialist urgently (within 24 hours). "
                "You likely need X-rays or advanced imaging to rule out fracture. "
                "In the meantime: apply ice, elevate the limb, limit movement, "
                "use over-the-counter pain relief if tolerated. "
                "Seek ER care if numbness, tingling, or color changes develop."
            )
        
        elif routing.escalation_level == EscalationLevel.OFFICE:
            return (
                "Schedule an orthopedic appointment within 1-2 weeks. "
                "Follow RICE protocol: Rest, Ice (15 mins, 3x/day), Compression, Elevation. "
                "Use over-the-counter anti-inflammatory medication if tolerated. "
                "Avoid activities that aggravate symptoms. "
                "Imaging may be needed depending on examination findings."
            )
        
        else:  # MONITOR_HOME
            return (
                "Monitor the injury at home with RICE protocol: "
                "Rest the joint, Ice for 15 minutes 3 times daily, use Compression bandage, "
                "Elevate above heart level. "
                "Most minor sprains resolve in 1-2 weeks. "
                "Contact a provider if swelling worsens, pain increases, or you cannot bear weight."
            )


class MockOrthopedicsAgent(BaseAgent):
    """Mock orthopedics agent for testing."""

    def __init__(self):
        super().__init__("Orthopedics")

    def generate_questions(self, symptoms: SymptomExtraction, routing: RoutingDecision) -> List[str]:
        """Return mock orthopedics questions."""
        return [
            "How did you injure this joint? Was there a fall or twisting motion?",
            "Can you move the joint? Is there visible swelling?",
            "Do you have numbness or tingling in the area?",
        ]

    def generate_recommendations(self, symptoms: SymptomExtraction, routing: RoutingDecision) -> str:
        """Return mock orthopedics recommendations."""
        return "Follow RICE protocol (Rest, Ice, Compression, Elevation). Schedule an orthopedic appointment if symptoms persist."
