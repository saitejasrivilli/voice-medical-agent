"""
Observability and metrics collection for monitoring and debugging.
"""

import logging
import logging.handlers
import json
import time
from datetime import datetime
from typing import Dict, Any, Optional
from functools import wraps
import uuid

from src.config import settings

# Configure structured logging
def setup_logging():
    """Configure JSON structured logging."""
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, settings.log_level))
    
    # Remove existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    if settings.log_format == "json":
        handler = logging.StreamHandler()
        handler.setFormatter(JsonFormatter())
    else:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
    
    logger.addHandler(handler)
    return logger


class JsonFormatter(logging.Formatter):
    """JSON formatter for structured logging."""

    def format(self, record):
        """Format log record as JSON."""
        log_obj = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
        }
        
        # Add exception info if present
        if record.exc_info:
            log_obj['exception'] = self.formatException(record.exc_info)
        
        # Add custom fields
        if hasattr(record, 'request_id'):
            log_obj['request_id'] = record.request_id
        if hasattr(record, 'assessment_id'):
            log_obj['assessment_id'] = record.assessment_id
        
        return json.dumps(log_obj)


class MetricsCollector:
    """Collect and aggregate performance metrics."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.metrics = {}

    def record_latency(
        self,
        stage: str,
        latency_ms: int,
        request_id: str = None,
        assessment_id: str = None,
    ):
        """Record stage latency."""
        self.logger.info(
            f"Stage {stage} latency: {latency_ms}ms",
            extra={
                'request_id': request_id,
                'assessment_id': assessment_id,
                'stage': stage,
                'latency_ms': latency_ms,
            }
        )

    def record_assessment(
        self,
        assessment_id: str,
        specialty: str,
        confidence: float,
        escalation_level: str,
        total_latency_ms: int,
        success: bool = True,
        error_message: str = None,
    ):
        """Record assessment completion."""
        self.logger.info(
            f"Assessment completed: {specialty} ({confidence:.2%}) -> {escalation_level}",
            extra={
                'assessment_id': assessment_id,
                'specialty': specialty,
                'confidence': confidence,
                'escalation_level': escalation_level,
                'total_latency_ms': total_latency_ms,
                'success': success,
                'error_message': error_message,
            }
        )

    def record_error(
        self,
        error_type: str,
        error_message: str,
        request_id: str = None,
        assessment_id: str = None,
        context: Dict[str, Any] = None,
    ):
        """Record error for analysis."""
        self.logger.error(
            f"{error_type}: {error_message}",
            extra={
                'request_id': request_id,
                'assessment_id': assessment_id,
                'error_type': error_type,
                'context': context or {},
            }
        )


def track_latency(stage_name: str):
    """Decorator to track function latency."""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start = time.time()
            result = await func(*args, **kwargs)
            latency_ms = int((time.time() - start) * 1000)
            
            logger = logging.getLogger(func.__module__)
            logger.info(
                f"{stage_name} completed in {latency_ms}ms",
                extra={'stage': stage_name, 'latency_ms': latency_ms}
            )
            return result
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start = time.time()
            result = func(*args, **kwargs)
            latency_ms = int((time.time() - start) * 1000)
            
            logger = logging.getLogger(func.__module__)
            logger.info(
                f"{stage_name} completed in {latency_ms}ms",
                extra={'stage': stage_name, 'latency_ms': latency_ms}
            )
            return result
        
        # Return async or sync wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator


def generate_request_id() -> str:
    """Generate unique request ID for tracking."""
    return str(uuid.uuid4())


# Global metrics collector
metrics = MetricsCollector()

# Setup logging on import
setup_logging()

import asyncio
