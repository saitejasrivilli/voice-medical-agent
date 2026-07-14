"""
SQLAlchemy ORM models for database persistence.
Handles assessments, audit logs, and metrics storage.
"""

from sqlalchemy import (
    Column, String, Float, DateTime, JSON, Integer, Boolean, 
    Text, Index, create_engine, event
)
from sqlalchemy.orm import declarative_base, Session
from sqlalchemy.sql import func
from datetime import datetime
import uuid
from typing import Optional

Base = declarative_base()


class Assessment(Base):
    """Assessment record - main entity for medical symptom assessments."""
    __tablename__ = "assessments"

    # Primary identifier
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Audio and transcription
    audio_file_hash = Column(String(64), unique=True, nullable=False, index=True)
    audio_size_bytes = Column(Integer, nullable=False)
    transcription = Column(Text, nullable=False)

    # Symptom extraction
    symptoms = Column(JSON, nullable=False)  # List of symptoms
    severity = Column(String(20), nullable=False, index=True)  # low, moderate, high, critical
    duration_days = Column(Integer, nullable=True)
    onset_type = Column(String(20), nullable=True)  # sudden, gradual, unknown
    associated_symptoms = Column(JSON, default={})

    # Routing results
    specialty = Column(String(50), nullable=False, index=True)  # cardiology, orthopedics, etc.
    routing_confidence = Column(Float, nullable=False)
    escalation_level = Column(String(30), nullable=False, index=True)  # ER, urgent_office, etc.
    escalation_reasoning = Column(Text, nullable=True)
    requires_immediate_attention = Column(Boolean, default=False, index=True)

    # Agent response
    agent_questions = Column(JSON, nullable=False)  # List of follow-up questions
    agent_recommendations = Column(Text, nullable=True)

    # Quality metrics
    overall_confidence = Column(Float, nullable=False)

    # Performance metrics
    transcription_latency_ms = Column(Integer, nullable=True)
    extraction_latency_ms = Column(Integer, nullable=True)
    routing_latency_ms = Column(Integer, nullable=True)
    agent_response_latency_ms = Column(Integer, nullable=True)
    total_latency_ms = Column(Integer, nullable=True)

    # Audit trail
    is_reviewed = Column(Boolean, default=False, index=True)
    clinical_reviewer_id = Column(String(36), nullable=True)
    clinical_reviewer_notes = Column(Text, nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    
    # Data lineage
    version = Column(String(10), default="1.0.0")
    is_test = Column(Boolean, default=False, index=True)

    __table_args__ = (
        Index('idx_created_specialty', 'created_at', 'specialty'),
        Index('idx_severity_escalation', 'severity', 'escalation_level'),
        Index('idx_audio_hash', 'audio_file_hash'),
    )

    def to_dict(self):
        """Convert to dictionary for serialization."""
        return {
            'id': self.id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'transcription': self.transcription,
            'symptoms': self.symptoms,
            'severity': self.severity,
            'specialty': self.specialty,
            'routing_confidence': self.routing_confidence,
            'escalation_level': self.escalation_level,
            'agent_questions': self.agent_questions,
            'agent_recommendations': self.agent_recommendations,
            'total_latency_ms': self.total_latency_ms,
        }


class AuditLog(Base):
    """Audit log for compliance and debugging."""
    __tablename__ = "audit_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    assessment_id = Column(String(36), nullable=True, index=True)
    
    # What happened
    action = Column(String(100), nullable=False, index=True)  # created, routed, reviewed, etc.
    action_type = Column(String(50), nullable=False)  # INFO, WARNING, ERROR
    
    # Who/what did it
    actor = Column(String(100), nullable=False)  # system, reviewer_id, etc.
    
    # Details
    details = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    
    # Status
    status = Column(String(20), nullable=False)  # success, failure

    __table_args__ = (
        Index('idx_assessment_id', 'assessment_id'),
        Index('idx_action_type', 'action_type'),
        Index('idx_created_at', 'created_at'),
    )


class PerformanceMetrics(Base):
    """Aggregated performance metrics for monitoring."""
    __tablename__ = "performance_metrics"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Counts
    total_assessments = Column(Integer, default=0)
    successful_assessments = Column(Integer, default=0)
    failed_assessments = Column(Integer, default=0)
    
    # Latency stats (in milliseconds)
    avg_transcription_latency_ms = Column(Float, nullable=True)
    avg_routing_latency_ms = Column(Float, nullable=True)
    avg_agent_response_latency_ms = Column(Float, nullable=True)
    avg_total_latency_ms = Column(Float, nullable=True)
    
    p95_total_latency_ms = Column(Float, nullable=True)
    p99_total_latency_ms = Column(Float, nullable=True)
    
    # Distribution
    specialty_distribution = Column(JSON, nullable=True)  # {specialty: count}
    severity_distribution = Column(JSON, nullable=True)  # {severity: count}
    escalation_distribution = Column(JSON, nullable=True)  # {level: count}
    
    # Quality
    avg_confidence_score = Column(Float, nullable=True)
    
    # Aggregation window
    time_window = Column(String(20), nullable=False)  # hourly, daily, monthly

    __table_args__ = (
        Index('idx_time_window', 'time_window'),
        Index('idx_created_at', 'created_at'),
    )


def init_db(database_url: str):
    """Initialize database and create tables."""
    engine = create_engine(
        database_url,
        echo=False,
        pool_size=5,
        max_overflow=10,
    )
    
    Base.metadata.create_all(engine)
    return engine


def get_session(engine):
    """Get SQLAlchemy session."""
    from sqlalchemy.orm import sessionmaker
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
    return SessionLocal()
