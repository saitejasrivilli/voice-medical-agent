"""
Pydantic models for request/response validation and data serialization.
"""

from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from uuid import UUID
from typing import Optional, List
from app.core.enums import Severity, Specialty, EscalationLevel


class SymptomExtraction(BaseModel):
    """Extracted symptoms from transcription."""
    symptoms: List[str] = Field(
        ..., 
        min_length=1, 
        max_length=10,
        description="List of detected symptoms"
    )
    severity: Severity = Field(..., description="Overall severity assessment")
    duration_days: Optional[int] = Field(
        None,
        ge=0,
        description="Days symptom has been present"
    )
    onset: Optional[str] = Field(
        None,
        description="Onset type: sudden, gradual, or unknown"
    )
    associated_symptoms: List[str] = Field(
        default_factory=list,
        description="Related symptoms mentioned"
    )

    @field_validator('symptoms')
    @classmethod
    def validate_symptoms(cls, v):
        """Ensure symptoms are non-empty strings."""
        if not v:
            raise ValueError("At least one symptom required")
        for symptom in v:
            if not isinstance(symptom, str) or not symptom.strip():
                raise ValueError("Symptoms must be non-empty strings")
        return [s.lower().strip() for s in v]

    @field_validator('onset')
    @classmethod
    def validate_onset(cls, v):
        """Validate onset is one of expected values."""
        if v and v.lower() not in ['sudden', 'gradual', 'unknown']:
            raise ValueError("Onset must be 'sudden', 'gradual', or 'unknown'")
        return v.lower() if v else None


class RoutingDecision(BaseModel):
    """Specialty routing decision with confidence scoring."""
    specialty: Specialty = Field(..., description="Target medical specialty")
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence score for routing decision"
    )
    reasoning: str = Field(..., description="Why this specialty was chosen")
    escalation_level: EscalationLevel = Field(
        ...,
        description="Patient escalation urgency level"
    )
    estimated_wait_time_hours: Optional[int] = Field(
        None,
        ge=0,
        description="Estimated wait time for appointment (if applicable)"
    )
    requires_immediate_attention: bool = Field(
        default=False,
        description="Whether patient needs immediate medical attention"
    )

    @field_validator('confidence')
    @classmethod
    def validate_confidence(cls, v):
        """Ensure confidence is reasonable."""
        if v < 0 or v > 1:
            raise ValueError("Confidence must be between 0 and 1")
        return round(v, 3)


class AssessmentOutput(BaseModel):
    """Complete assessment output from the pipeline."""
    id: UUID = Field(..., description="Unique assessment ID")
    created_at: datetime = Field(..., description="Creation timestamp")
    transcription: str = Field(..., description="Transcribed audio text")
    symptoms: SymptomExtraction = Field(..., description="Extracted symptoms")
    routing: RoutingDecision = Field(..., description="Routing decision")
    agent_questions: List[str] = Field(..., description="Follow-up questions from agent")
    agent_recommendations: str = Field(..., description="Agent's clinical recommendations")
    confidence_in_assessment: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Overall confidence in assessment"
    )
    processing_latency_ms: int = Field(..., ge=0, description="Total processing time")
    transcription_latency_ms: Optional[int] = Field(
        None,
        ge=0,
        description="Time to transcribe audio"
    )
    routing_latency_ms: Optional[int] = Field(
        None,
        ge=0,
        description="Time to route to specialty"
    )


class TranscriptionRequest(BaseModel):
    """Request to transcribe audio from file path (internal use)."""
    audio_path: str = Field(..., description="Path to audio file")
    language: str = Field(default="en", description="Language of audio")


class TranscriptionResponse(BaseModel):
    """Response from transcription service."""
    text: str = Field(..., description="Transcribed text")
    confidence: Optional[float] = Field(
        None,
        description="Transcription confidence score"
    )
    language: str = Field(..., description="Detected language")
    duration_seconds: Optional[float] = Field(
        None,
        description="Audio duration in seconds"
    )


class HealthCheckResponse(BaseModel):
    """Health check response."""
    status: str = Field(..., description="Service status")
    timestamp: datetime = Field(..., description="Health check time")
    groq_api_available: bool = Field(..., description="Groq API connectivity")
    database_available: bool = Field(..., description="Database connectivity")
    version: str = Field(default="1.0.0", description="API version")


class ErrorResponse(BaseModel):
    """Standardized error response."""
    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Detailed error information")
    request_id: Optional[str] = Field(None, description="Request tracking ID")
    timestamp: datetime = Field(..., description="Error timestamp")


class MetricsSnapshot(BaseModel):
    """Metrics for monitoring and observability."""
    total_assessments: int = Field(..., description="Total assessments processed")
    success_rate: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Percentage of successful assessments"
    )
    avg_latency_ms: float = Field(..., description="Average processing latency")
    specialty_distribution: dict = Field(..., description="Counts by specialty")
    escalation_distribution: dict = Field(..., description="Counts by escalation level")
    last_updated: datetime = Field(..., description="Metrics snapshot time")
