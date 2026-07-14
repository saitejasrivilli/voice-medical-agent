"""
Unit tests for medical voice agent components.
"""

import pytest
import sys
import os
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.core.models import SymptomExtraction, RoutingDecision
from src.core.enums import Severity, Specialty, EscalationLevel
from src.agents.symptom_extractor import MockExtractor
from src.agents.specialty_router import MockRouter
from src.agents.cardiology_agent import MockCardiologyAgent
from src.agents.orthopedics_agent import MockOrthopedicsAgent
from src.agents.dermatology_agent import MockDermatologyAgent
from src.agents.triage_agent import MockGeneralTriageAgent


class TestSymptomExtraction:
    """Test symptom extraction."""

    def test_extract_chest_pain(self):
        """Test extraction of cardiac symptoms."""
        extractor = MockExtractor()
        
        symptoms = extractor.extract(
            "I have severe chest pain and shortness of breath"
        )
        
        assert "chest pain" in symptoms.symptoms
        assert "shortness of breath" in symptoms.symptoms
        assert symptoms.severity == Severity.CRITICAL

    def test_extract_joint_pain(self):
        """Test extraction of orthopedic symptoms."""
        extractor = MockExtractor()
        
        symptoms = extractor.extract(
            "My knee is swollen and painful after falling"
        )
        
        assert len(symptoms.symptoms) > 0
        assert symptoms.severity == Severity.MODERATE

    def test_extract_rash(self):
        """Test extraction of dermatologic symptoms."""
        extractor = MockExtractor()
        
        symptoms = extractor.extract(
            "I have a red rash on my arm for 3 weeks"
        )
        
        assert "rash" in symptoms.symptoms
        assert symptoms.severity == Severity.LOW
        assert symptoms.duration_days == 21


class TestSpecialtyRouting:
    """Test specialty routing."""

    def test_route_to_cardiology(self):
        """Test routing to cardiology."""
        router = MockRouter()
        symptoms = SymptomExtraction(
            symptoms=["chest pain", "shortness of breath"],
            severity=Severity.CRITICAL,
        )
        
        routing = router.route(symptoms)
        
        assert routing.specialty == Specialty.CARDIOLOGY
        assert routing.escalation_level == EscalationLevel.ER
        assert routing.requires_immediate_attention

    def test_route_to_orthopedics(self):
        """Test routing to orthopedics."""
        router = MockRouter()
        symptoms = SymptomExtraction(
            symptoms=["joint pain", "swelling"],
            severity=Severity.MODERATE,
        )
        
        routing = router.route(symptoms)
        
        assert routing.specialty == Specialty.ORTHOPEDICS
        assert routing.escalation_level == EscalationLevel.OFFICE

    def test_route_to_dermatology(self):
        """Test routing to dermatology."""
        router = MockRouter()
        symptoms = SymptomExtraction(
            symptoms=["rash", "itching"],
            severity=Severity.LOW,
        )
        
        routing = router.route(symptoms)
        
        assert routing.specialty == Specialty.DERMATOLOGY
        assert routing.escalation_level == EscalationLevel.OFFICE


class TestCardiologyAgent:
    """Test cardiology agent."""

    def test_cardiology_questions_er(self):
        """Test cardiology questions for ER-level symptoms."""
        agent = MockCardiologyAgent()
        symptoms = SymptomExtraction(
            symptoms=["chest pain", "shortness of breath"],
            severity=Severity.CRITICAL,
        )
        routing = RoutingDecision(
            specialty=Specialty.CARDIOLOGY,
            confidence=0.9,
            reasoning="Cardiac symptoms",
            escalation_level=EscalationLevel.ER,
        )
        
        questions, recommendations = agent.get_assessment(symptoms, routing)
        
        assert len(questions) > 0
        assert "911" in recommendations.lower() or "emergency" in recommendations.lower()

    def test_cardiology_questions_office(self):
        """Test cardiology questions for office-level symptoms."""
        agent = MockCardiologyAgent()
        symptoms = SymptomExtraction(
            symptoms=["chest pain"],
            severity=Severity.MODERATE,
        )
        routing = RoutingDecision(
            specialty=Specialty.CARDIOLOGY,
            confidence=0.8,
            reasoning="Cardiac symptoms",
            escalation_level=EscalationLevel.OFFICE,
        )
        
        questions, recommendations = agent.get_assessment(symptoms, routing)
        
        assert len(questions) > 0
        assert "cardiology" in recommendations.lower()


class TestOrthopedicsAgent:
    """Test orthopedics agent."""

    def test_orthopedics_questions(self):
        """Test orthopedics questions."""
        agent = MockOrthopedicsAgent()
        symptoms = SymptomExtraction(
            symptoms=["joint pain", "swelling"],
            severity=Severity.MODERATE,
        )
        routing = RoutingDecision(
            specialty=Specialty.ORTHOPEDICS,
            confidence=0.85,
            reasoning="Orthopedic symptoms",
            escalation_level=EscalationLevel.OFFICE,
        )
        
        questions, recommendations = agent.get_assessment(symptoms, routing)
        
        assert len(questions) > 0
        assert "RICE" in recommendations.upper()


class TestDermatologyAgent:
    """Test dermatology agent."""

    def test_dermatology_questions(self):
        """Test dermatology questions."""
        agent = MockDermatologyAgent()
        symptoms = SymptomExtraction(
            symptoms=["rash", "itching"],
            severity=Severity.LOW,
        )
        routing = RoutingDecision(
            specialty=Specialty.DERMATOLOGY,
            confidence=0.75,
            reasoning="Dermatologic symptoms",
            escalation_level=EscalationLevel.OFFICE,
        )
        
        questions, recommendations = agent.get_assessment(symptoms, routing)
        
        assert len(questions) > 0
        assert "dermatology" in recommendations.lower()


class TestTriageAgent:
    """Test general triage agent."""

    def test_triage_questions(self):
        """Test triage questions."""
        agent = MockGeneralTriageAgent()
        symptoms = SymptomExtraction(
            symptoms=["general symptoms"],
            severity=Severity.MODERATE,
        )
        routing = RoutingDecision(
            specialty=Specialty.GENERAL_TRIAGE,
            confidence=0.5,
            reasoning="Unclear specialty",
            escalation_level=EscalationLevel.OFFICE,
        )
        
        questions, recommendations = agent.get_assessment(symptoms, routing)
        
        assert len(questions) > 0
        assert "primary care" in recommendations.lower() or "doctor" in recommendations.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
