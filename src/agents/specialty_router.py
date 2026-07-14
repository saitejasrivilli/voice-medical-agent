"""
Specialty routing service - routes symptoms to appropriate medical specialty.
Uses keyword matching with confidence scoring and specialty-specific escalation logic.
"""
from src.core.enums import EscalationLevel, Specialty
import logging
from typing import List, Tuple
from src.core.models import SymptomExtraction, RoutingDecision
from src.core.enums import (
    Specialty, Severity, EscalationLevel, 
    SPECIALTY_KEYWORDS, CONFIDENCE_THRESHOLD,
    CARDIOLOGY_CRITICAL, ORTHOPEDICS_CRITICAL, DERMATOLOGY_CRITICAL
)

logger = logging.getLogger(__name__)


class SpecialtyRoutingError(Exception):
    """Routing error."""
    pass


class SpecialtyRouter:
    """Route patient symptoms to appropriate medical specialty."""

    def __init__(self, confidence_threshold: float = CONFIDENCE_THRESHOLD):
        """
        Initialize router.
        
        Args:
            confidence_threshold: Route to general triage if confidence below this
        """
        self.confidence_threshold = confidence_threshold
        self.specialty_keywords = SPECIALTY_KEYWORDS
    def _get_escalation(self, specialty, symptoms):
         
        if specialty == Specialty.CARDIOLOGY:
            if symptoms.severity == "high":
                return EscalationLevel.ER
            return EscalationLevel.URGENT_OFFICE
        
        if specialty == Specialty.ORTHOPEDICS:
            if symptoms.severity == "high":
                return EscalationLevel.URGENT_OFFICE
            return EscalationLevel.OFFICE
        
        return EscalationLevel.OFFICE
    def route(self, symptoms: SymptomExtraction) -> RoutingDecision:
        import pickle
        
        # Load model
        with open("specialty_router_model.pkl", "rb") as f:
            clf, vectorizer = pickle.load(f)
        
        # Prepare text
        text = f"{' '.join(symptoms.symptoms)} {symptoms.severity}"
        
        # Predict
        vec = vectorizer.transform([text])
        specialty_str = clf.predict(vec)[0]
        confidence = clf.predict_proba(vec)[0].max()
        
        # Map to enum
        specialty_map = {
            'cardiology': Specialty.CARDIOLOGY,
            'orthopedics': Specialty.ORTHOPEDICS,
            'dermatology': Specialty.DERMATOLOGY,
            'general_triage': Specialty.GENERAL_TRIAGE,
        }
        
        specialty = specialty_map.get(specialty_str, Specialty.GENERAL_TRIAGE)
        
        # Determine escalation
        escalation_level = self._get_escalation(specialty, symptoms)
        
        return RoutingDecision(
            specialty=specialty,
            confidence=confidence,
            reasoning=f"ML model prediction: {specialty_str} ({confidence:.1%})",
            escalation_level=escalation_level,
            requires_immediate_attention=escalation_level == EscalationLevel.ER
    )
    def _calculate_specialty_scores(
        self,
        symptom_text: str,
        symptoms: List[str]
    ) -> dict:
        """
        Calculate confidence score for each specialty.
        
        Returns:
            Dict mapping specialty to confidence score (0-1)
        """
        scores = {}
        
        for specialty, keywords in self.specialty_keywords.items():
            if not keywords:
                scores[specialty] = 0.0
                continue
            
            # Count keyword matches
            matches = 0
            for keyword in keywords:
                if keyword in symptom_text:
                    matches += 1
            
            # Calculate confidence as percentage of keywords matched
            confidence = matches / len(keywords) if keywords else 0
            scores[specialty] = confidence
        
        return scores

    def _determine_escalation(
        self,
        specialty: Specialty,
        severity: Severity,
        symptoms: List[str]
    ) -> EscalationLevel:
        """Determine escalation level based on specialty and severity."""
        
        symptom_text = " ".join(symptoms).lower()
        
        if specialty == Specialty.CARDIOLOGY:
            return self._cardiology_escalation(severity, symptom_text)
        elif specialty == Specialty.ORTHOPEDICS:
            return self._orthopedics_escalation(severity, symptom_text)
        elif specialty == Specialty.DERMATOLOGY:
            return self._dermatology_escalation(severity, symptom_text)
        else:  # GENERAL_TRIAGE
            return self._general_triage_escalation(severity)

    def _cardiology_escalation(self, severity: Severity, symptom_text: str) -> EscalationLevel:
        """Cardiology-specific escalation logic."""
        # Check for critical symptoms
        for critical in CARDIOLOGY_CRITICAL:
            if critical in symptom_text:
                return EscalationLevel.ER
        
        # Escalate by severity
        if severity == Severity.CRITICAL:
            return EscalationLevel.ER
        elif severity == Severity.HIGH:
            return EscalationLevel.URGENT_OFFICE
        elif severity == Severity.MODERATE:
            return EscalationLevel.OFFICE
        else:
            return EscalationLevel.MONITOR_HOME

    def _orthopedics_escalation(self, severity: Severity, symptom_text: str) -> EscalationLevel:
        """Orthopedics-specific escalation logic."""
        # Check for critical symptoms
        for critical in ORTHOPEDICS_CRITICAL:
            if critical in symptom_text:
                return EscalationLevel.ER
        
        # Escalate by severity
        if severity == Severity.CRITICAL:
            return EscalationLevel.ER
        elif severity == Severity.HIGH:
            return EscalationLevel.URGENT_OFFICE
        else:
            return EscalationLevel.OFFICE

    def _dermatology_escalation(self, severity: Severity, symptom_text: str) -> EscalationLevel:
        """Dermatology-specific escalation logic."""
        # Check for critical symptoms (dermatology rarely needs ER)
        for critical in DERMATOLOGY_CRITICAL:
            if critical in symptom_text:
                return EscalationLevel.URGENT_OFFICE
        
        # Escalate by severity
        if severity == Severity.CRITICAL:
            return EscalationLevel.URGENT_OFFICE
        elif severity == Severity.HIGH:
            return EscalationLevel.OFFICE
        else:
            return EscalationLevel.OFFICE

    def _general_triage_escalation(self, severity: Severity) -> EscalationLevel:
        """General triage escalation - used when specialty unclear."""
        if severity == Severity.CRITICAL:
            return EscalationLevel.ER
        elif severity == Severity.HIGH:
            return EscalationLevel.URGENT_OFFICE
        elif severity == Severity.MODERATE:
            return EscalationLevel.OFFICE
        else:
            return EscalationLevel.MONITOR_HOME


class MockRouter:
    """Mock router for testing."""

    def route(self, symptoms: SymptomExtraction) -> RoutingDecision:
        """Return mock routing decision."""
        symptom_text = " ".join(symptoms.symptoms).lower()
        
        if "chest" in symptom_text or "heart" in symptom_text:
            return RoutingDecision(
                specialty=Specialty.CARDIOLOGY,
                confidence=0.85,
                reasoning="Chest/heart symptoms detected",
                escalation_level=EscalationLevel.ER if symptoms.severity == Severity.CRITICAL else EscalationLevel.OFFICE,
                requires_immediate_attention=symptoms.severity in [Severity.CRITICAL, Severity.HIGH],
            )
        elif "knee" in symptom_text or "ankle" in symptom_text or "joint" in symptom_text:
            return RoutingDecision(
                specialty=Specialty.ORTHOPEDICS,
                confidence=0.80,
                reasoning="Joint/orthopedic symptoms detected",
                escalation_level=EscalationLevel.OFFICE,
                requires_immediate_attention=False,
            )
        elif "rash" in symptom_text or "skin" in symptom_text:
            return RoutingDecision(
                specialty=Specialty.DERMATOLOGY,
                confidence=0.75,
                reasoning="Dermatologic symptoms detected",
                escalation_level=EscalationLevel.OFFICE,
                requires_immediate_attention=False,
            )
        else:
            return RoutingDecision(
                specialty=Specialty.GENERAL_TRIAGE,
                confidence=0.50,
                reasoning="General triage needed",
                escalation_level=EscalationLevel.OFFICE,
                requires_immediate_attention=False,
            )
