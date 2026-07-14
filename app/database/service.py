"""
Database service layer - handles all CRUD operations and data access.
"""

from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from datetime import datetime, timedelta
from typing import Optional, List, Dict
import json

from app.database.models import Assessment, AuditLog, PerformanceMetrics
from app.core.enums import Specialty, EscalationLevel


class AssessmentService:
    """Service for managing Assessment records."""

    def __init__(self, session: Session):
        self.session = session

    def create_assessment(
        self,
        audio_file_hash: str,
        audio_size_bytes: int,
        transcription: str,
        symptoms: list,
        severity: str,
        specialty: str,
        routing_confidence: float,
        escalation_level: str,
        agent_questions: list,
        agent_recommendations: str,
        overall_confidence: float,
        latency_ms: int,
        transcription_latency_ms: Optional[int] = None,
        extraction_latency_ms: Optional[int] = None,
        routing_latency_ms: Optional[int] = None,
        agent_response_latency_ms: Optional[int] = None,
        duration_days: Optional[int] = None,
        onset_type: Optional[str] = None,
        requires_immediate_attention: bool = False,
    ) -> Assessment:
        """Create new assessment record."""
        assessment = Assessment(
            audio_file_hash=audio_file_hash,
            audio_size_bytes=audio_size_bytes,
            transcription=transcription,
            symptoms=symptoms,
            severity=severity,
            specialty=specialty,
            routing_confidence=routing_confidence,
            escalation_level=escalation_level,
            agent_questions=agent_questions,
            agent_recommendations=agent_recommendations,
            overall_confidence=overall_confidence,
            total_latency_ms=latency_ms,
            transcription_latency_ms=transcription_latency_ms,
            extraction_latency_ms=extraction_latency_ms,
            routing_latency_ms=routing_latency_ms,
            agent_response_latency_ms=agent_response_latency_ms,
            duration_days=duration_days,
            onset_type=onset_type,
            requires_immediate_attention=requires_immediate_attention,
        )
        self.session.add(assessment)
        self.session.commit()
        self.session.refresh(assessment)
        return assessment

    def get_assessment(self, assessment_id: str) -> Optional[Assessment]:
        """Get assessment by ID."""
        return self.session.query(Assessment).filter(
            Assessment.id == assessment_id
        ).first()

    def get_assessments_by_specialty(
        self,
        specialty: str,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Assessment]:
        """Get all assessments for a specialty."""
        return self.session.query(Assessment).filter(
            Assessment.specialty == specialty
        ).order_by(
            desc(Assessment.created_at)
        ).limit(limit).offset(offset).all()

    def get_assessments_by_date_range(
        self,
        start_date: datetime,
        end_date: datetime,
        limit: int = 100,
    ) -> List[Assessment]:
        """Get assessments within date range."""
        return self.session.query(Assessment).filter(
            Assessment.created_at >= start_date,
            Assessment.created_at <= end_date,
        ).order_by(
            desc(Assessment.created_at)
        ).limit(limit).all()

    def get_high_severity_assessments(
        self,
        days_back: int = 7,
    ) -> List[Assessment]:
        """Get high and critical severity assessments from recent days."""
        cutoff = datetime.utcnow() - timedelta(days=days_back)
        return self.session.query(Assessment).filter(
            Assessment.created_at >= cutoff,
            Assessment.severity.in_(['high', 'critical']),
        ).order_by(
            desc(Assessment.created_at)
        ).all()

    def get_requiring_attention(self) -> List[Assessment]:
        """Get all assessments requiring immediate attention."""
        return self.session.query(Assessment).filter(
            Assessment.requires_immediate_attention == True,
            Assessment.is_reviewed == False,
        ).order_by(
            Assessment.created_at
        ).all()

    def update_assessment_review(
        self,
        assessment_id: str,
        reviewer_id: str,
        notes: str,
    ) -> Assessment:
        """Mark assessment as reviewed."""
        assessment = self.get_assessment(assessment_id)
        if assessment:
            assessment.is_reviewed = True
            assessment.clinical_reviewer_id = reviewer_id
            assessment.clinical_reviewer_notes = notes
            assessment.reviewed_at = datetime.utcnow()
            self.session.commit()
            self.session.refresh(assessment)
        return assessment

    def check_duplicate_audio(self, audio_hash: str) -> bool:
        """Check if audio file already processed (deduplication)."""
        return self.session.query(Assessment).filter(
            Assessment.audio_file_hash == audio_hash
        ).first() is not None


class AuditService:
    """Service for managing audit logs."""

    def __init__(self, session: Session):
        self.session = session

    def log_action(
        self,
        action: str,
        action_type: str,
        actor: str,
        assessment_id: Optional[str] = None,
        details: Optional[Dict] = None,
        error_message: Optional[str] = None,
        status: str = "success",
    ) -> AuditLog:
        """Create audit log entry."""
        audit_log = AuditLog(
            assessment_id=assessment_id,
            action=action,
            action_type=action_type,
            actor=actor,
            details=details or {},
            error_message=error_message,
            status=status,
        )
        self.session.add(audit_log)
        self.session.commit()
        return audit_log

    def get_assessment_audit_trail(self, assessment_id: str) -> List[AuditLog]:
        """Get all audit logs for an assessment."""
        return self.session.query(AuditLog).filter(
            AuditLog.assessment_id == assessment_id
        ).order_by(
            AuditLog.created_at
        ).all()

    def get_recent_errors(self, hours_back: int = 24) -> List[AuditLog]:
        """Get recent error logs."""
        cutoff = datetime.utcnow() - timedelta(hours=hours_back)
        return self.session.query(AuditLog).filter(
            AuditLog.created_at >= cutoff,
            AuditLog.action_type == "ERROR",
        ).order_by(
            desc(AuditLog.created_at)
        ).all()


class MetricsService:
    """Service for managing performance metrics."""

    def __init__(self, session: Session):
        self.session = session

    def create_metrics_snapshot(
        self,
        time_window: str = "hourly",
    ) -> PerformanceMetrics:
        """Create aggregated metrics snapshot."""
        # Get total and successful assessments
        total = self.session.query(Assessment).count()
        successful = self.session.query(Assessment).filter(
            Assessment.total_latency_ms.isnot(None)
        ).count()
        failed = total - successful

        # Get latency stats
        latencies = self.session.query(Assessment).filter(
            Assessment.total_latency_ms.isnot(None)
        ).all()

        if latencies:
            avg_transcription = sum(
                a.transcription_latency_ms or 0 for a in latencies
            ) / len(latencies)
            avg_routing = sum(
                a.routing_latency_ms or 0 for a in latencies
            ) / len(latencies)
            avg_agent = sum(
                a.agent_response_latency_ms or 0 for a in latencies
            ) / len(latencies)
            avg_total = sum(a.total_latency_ms for a in latencies) / len(latencies)
            
            # Calculate percentiles
            sorted_latencies = sorted([a.total_latency_ms for a in latencies])
            p95_idx = int(len(sorted_latencies) * 0.95)
            p99_idx = int(len(sorted_latencies) * 0.99)
            p95 = sorted_latencies[p95_idx] if p95_idx < len(sorted_latencies) else None
            p99 = sorted_latencies[p99_idx] if p99_idx < len(sorted_latencies) else None
        else:
            avg_transcription = avg_routing = avg_agent = avg_total = p95 = p99 = None

        # Get distributions
        specialty_dist = {}
        for spec in self.session.query(Assessment.specialty, func.count()).group_by(
            Assessment.specialty
        ).all():
            specialty_dist[spec[0]] = spec[1]

        severity_dist = {}
        for sev in self.session.query(Assessment.severity, func.count()).group_by(
            Assessment.severity
        ).all():
            severity_dist[sev[0]] = sev[1]

        escalation_dist = {}
        for esc in self.session.query(
            Assessment.escalation_level, func.count()
        ).group_by(Assessment.escalation_level).all():
            escalation_dist[esc[0]] = esc[1]

        # Get average confidence
        avg_confidence = self.session.query(
            func.avg(Assessment.overall_confidence)
        ).scalar()

        metrics = PerformanceMetrics(
            total_assessments=total,
            successful_assessments=successful,
            failed_assessments=failed,
            avg_transcription_latency_ms=avg_transcription,
            avg_routing_latency_ms=avg_routing,
            avg_agent_response_latency_ms=avg_agent,
            avg_total_latency_ms=avg_total,
            p95_total_latency_ms=p95,
            p99_total_latency_ms=p99,
            specialty_distribution=specialty_dist,
            severity_distribution=severity_dist,
            escalation_distribution=escalation_dist,
            avg_confidence_score=float(avg_confidence) if avg_confidence else None,
            time_window=time_window,
        )
        self.session.add(metrics)
        self.session.commit()
        return metrics

    def get_latest_metrics(self, time_window: str = "hourly") -> Optional[PerformanceMetrics]:
        """Get latest metrics snapshot."""
        return self.session.query(PerformanceMetrics).filter(
            PerformanceMetrics.time_window == time_window
        ).order_by(
            desc(PerformanceMetrics.created_at)
        ).first()
