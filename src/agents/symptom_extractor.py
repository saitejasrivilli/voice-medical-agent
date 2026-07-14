"""
Symptom extraction service - extracts structured medical information from transcription.
Uses LLM-based extraction with fallback to keyword matching.
"""

import logging
import json
import re
from typing import Optional
from src.core.models import SymptomExtraction
from src.core.enums import Severity

logger = logging.getLogger(__name__)


class SymptomExtractorError(Exception):
    """Symptom extraction error."""
    pass


class LLMBasedExtractor:
    """Extract symptoms using Groq LLM."""

    def __init__(self, api_key: Optional[str] = None):
        """Initialize with Groq API key."""
        try:
            from groq import Groq
            self.client = Groq(api_key=api_key)
        except ImportError:
            raise ImportError("Groq SDK not installed")

    def extract(self, transcription: str) -> SymptomExtraction:
        """
        Extract symptoms from transcription using LLM.
        
        Args:
            transcription: Patient's symptom description
            
        Returns:
            SymptomExtraction with structured data
        """
        prompt = f"""
Analyze this patient transcription and extract medical information in JSON format.

Transcription: "{transcription}"

Return ONLY a JSON object (no markdown, no extra text) with:
{{
  "symptoms": ["symptom1", "symptom2"],  // Main presenting symptoms (1-10 items)
  "severity": "low|moderate|high|critical",  // Overall severity assessment
  "duration_days": number or null,  // How many days if mentioned
  "onset": "sudden|gradual|unknown",  // How symptoms started
  "associated_symptoms": ["symptom3"]  // Secondary/related symptoms
}}

Rules:
- Symptoms: simple, lowercase, 1-3 words each
- Severity: based on symptom severity and urgency described
- Critical: life-threatening (chest pain, severe bleeding, difficulty breathing)
- High: severe but not immediately life-threatening
- Moderate: uncomfortable but manageable
- Low: mild symptoms
- Duration: extract number of days/hours/weeks mentioned
- Onset: sudden vs gradual (sudden = within minutes/hours, gradual = days/weeks)
"""

        try:
            response = self.client.messages.create(
                model="mixtral-8x7b-32768",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=500,
                temperature=0.3,
            )
            
            # Parse JSON from response
            response_text = response.content[0].text
            
            # Try to extract JSON from response
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if not json_match:
                logger.warning(f"Could not find JSON in response: {response_text}")
                return self._fallback_extract(transcription)
            
            json_str = json_match.group(0)
            data = json.loads(json_str)
            
            # Validate extracted data
            extracted = SymptomExtraction(
                symptoms=data.get("symptoms", []),
                severity=data.get("severity", "moderate"),
                duration_days=data.get("duration_days"),
                onset=data.get("onset", "unknown"),
                associated_symptoms=data.get("associated_symptoms", []),
            )
            
            logger.info(f"Extracted {len(extracted.symptoms)} symptoms, severity: {extracted.severity}")
            return extracted
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error in symptom extraction: {str(e)}")
            return self._fallback_extract(transcription)
        except Exception as e:
            logger.error(f"LLM extraction failed: {str(e)}")
            return self._fallback_extract(transcription)

    def _fallback_extract(self, transcription: str) -> SymptomExtraction:
        """Fallback keyword-based extraction."""
        logger.info("Using fallback keyword-based symptom extraction")
        
        text_lower = transcription.lower()
        
        # Common symptom keywords
        symptom_keywords = {
            "chest pain": ["chest pain", "chest ache", "chest discomfort"],
            "shortness of breath": ["shortness of breath", "breathless", "can't breathe", "difficulty breathing"],
            "swelling": ["swelling", "swollen", "edema"],
            "pain": ["pain", "hurts", "ache", "discomfort"],
            "rash": ["rash", "skin rash", "lesion"],
            "fever": ["fever", "high temperature", "hot"],
            "cough": ["cough", "coughing"],
            "nausea": ["nausea", "sick", "queasy"],
            "headache": ["headache", "head pain"],
            "dizziness": ["dizzy", "dizziness", "vertigo"],
            "weakness": ["weakness", "weak", "fatigued"],
        }
        
        symptoms = []
        for symptom, keywords in symptom_keywords.items():
            for keyword in keywords:
                if keyword in text_lower:
                    symptoms.append(symptom)
                    break
        
        # Estimate severity
        critical_words = ["severe", "worst", "unbearable", "can't breathe", "chest pain", "bleeding"]
        high_words = ["bad", "terrible", "very", "extremely"]
        low_words = ["mild", "slight", "little", "minor"]
        
        severity = Severity.MODERATE
        if any(word in text_lower for word in critical_words):
            severity = Severity.CRITICAL
        elif any(word in text_lower for word in high_words):
            severity = Severity.HIGH
        elif any(word in text_lower for word in low_words):
            severity = Severity.LOW
        
        # Extract duration
        duration_match = re.search(r'(\d+)\s*(day|days|hour|hours|week|weeks|month|months)', text_lower)
        duration_days = None
        if duration_match:
            num = int(duration_match.group(1))
            unit = duration_match.group(2)
            if 'day' in unit:
                duration_days = num
            elif 'hour' in unit:
                duration_days = num / 24
            elif 'week' in unit:
                duration_days = num * 7
            elif 'month' in unit:
                duration_days = num * 30
        
        # Determine onset
        onset = "unknown"
        if "suddenly" in text_lower or "sudden" in text_lower:
            onset = "sudden"
        elif "gradually" in text_lower or "slowly" in text_lower or "over time" in text_lower:
            onset = "gradual"
        
        if not symptoms:
            symptoms = ["general symptoms"]
        
        return SymptomExtraction(
            symptoms=symptoms[:10],  # Limit to 10
            severity=severity,
            duration_days=int(duration_days) if duration_days else None,
            onset=onset,
            associated_symptoms=[],
        )


class MockExtractor:
    """Mock symptom extractor for testing."""

    def extract(self, transcription: str) -> SymptomExtraction:
        """Return mock extraction."""
        text_lower = transcription.lower()
        
        # Simple mock logic based on text
        if "chest" in text_lower and "pain" in text_lower:
            return SymptomExtraction(
                symptoms=["chest pain", "shortness of breath"],
                severity=Severity.CRITICAL,
                duration_days=None,
                onset="sudden",
            )
        elif "knee" in text_lower or "ankle" in text_lower:
            return SymptomExtraction(
                symptoms=["joint pain", "swelling"],
                severity=Severity.MODERATE,
                duration_days=1,
                onset="sudden",
            )
        elif "rash" in text_lower:
            return SymptomExtraction(
                symptoms=["rash", "itching"],
                severity=Severity.LOW,
                duration_days=21,
                onset="gradual",
            )
        else:
            return SymptomExtraction(
                symptoms=["general symptoms"],
                severity=Severity.MODERATE,
                duration_days=None,
                onset="unknown",
            )
