"""
FastAPI application with main API endpoints for the medical voice agent.
"""

import logging
import time
import os
from fastapi import FastAPI, UploadFile, File, HTTPException, Request, Depends, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import asyncio
from sqlalchemy import text
from app.config import settings
from app.core.models import AssessmentOutput, HealthCheckResponse, ErrorResponse, SymptomExtraction, RoutingDecision
from app.database.models import init_db, Assessment as DBAssessment
from app.database.service import AssessmentService, AuditService
from app.services.transcriber import GroqTranscriber, MockTranscriber, TranscriptionError
from app.agents.symptom_extractor import LLMBasedExtractor, MockExtractor
from app.agents.specialty_router import SpecialtyRouter, MockRouter
from app.agents.factory import AgentFactory
from app.observability.logging import setup_logging, metrics, generate_request_id
from app.services.synthesizer import get_synthesizer, SynthesisError
from app.services.streaming_transcriber import StreamingSession, StreamResult
from app.pipeline import run_text_pipeline

# Setup logging
logger = setup_logging()
logger = logging.getLogger(__name__)

# Initialize FastAPI
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Production medical voice agent with specialty routing",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=settings.cors_allow_methods,
    allow_headers=settings.cors_allow_headers,
)

# Rate limiting
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, lambda request, exc: JSONResponse(
    status_code=429,
    content={"error": "Rate limit exceeded", "detail": str(exc)},
))

# Database initialization
engine = init_db(settings.database_url)
SessionLocal = sessionmaker(bind=engine)

# Service initialization
_transcriber = None
_extractor = None
_router = None

def get_transcriber():
    """Get or initialize transcriber."""
    global _transcriber
    if _transcriber is None:
        try:
            _transcriber = GroqTranscriber(api_key=settings.groq_api_key)
        except Exception as e:
            logger.warning(f"Failed to initialize Groq transcriber: {str(e)}, using mock")
            _transcriber = MockTranscriber()
    return _transcriber

def get_extractor():
    """Get or initialize symptom extractor."""
    global _extractor
    if _extractor is None:
        try:
            _extractor = LLMBasedExtractor(api_key=settings.groq_api_key)
        except Exception as e:
            logger.warning(f"Failed to initialize LLM extractor: {str(e)}, using mock")
            _extractor = MockExtractor()
    return _extractor

def get_router():
    """Get or initialize router."""
    global _router
    if _router is None:
        _router = SpecialtyRouter(
            confidence_threshold=settings.routing_confidence_threshold
        )
    return _router

def get_db():
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.middleware("http")
async def add_request_id(request: Request, call_next):
    """Add request ID to all requests."""
    request_id = generate_request_id()
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response

# ============================================================================
# Health and Status Endpoints
# ============================================================================

@app.get("/health", response_model=HealthCheckResponse)
async def health_check():
    """Health check endpoint."""
    return HealthCheckResponse(
        status="healthy",
        timestamp=datetime.utcnow(),
        groq_api_available=True,
        database_available=True,
        version=settings.app_version,
    )
@app.get("/metrics")
async def get_metrics(db: Session = Depends(get_db)):
    """Get aggregated metrics."""
    from app.database.service import MetricsService
    
    metrics_service = MetricsService(db)
    latest_metrics = metrics_service.get_latest_metrics()
    
    if not latest_metrics:
        return {
            "message": "No metrics available yet",
            "timestamp": datetime.utcnow(),
        }
    
    return {
        "total_assessments": latest_metrics.total_assessments,
        "successful_assessments": latest_metrics.successful_assessments,
        "success_rate": (latest_metrics.successful_assessments / latest_metrics.total_assessments 
                        if latest_metrics.total_assessments > 0 else 0),
        "avg_latency_ms": latest_metrics.avg_total_latency_ms,
        "specialty_distribution": latest_metrics.specialty_distribution,
        "escalation_distribution": latest_metrics.escalation_distribution,
        "timestamp": latest_metrics.created_at,
    }

# ============================================================================
# Assessment Endpoints
# ============================================================================
@app.post("/assess", response_model=AssessmentOutput)
@limiter.limit(f"{settings.rate_limit_per_minute}/minute")
async def assess_symptoms(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    Main assessment endpoint - accepts audio file and returns medical assessment.
    
    - Transcribes audio
    - Extracts symptoms
    - Routes to appropriate specialty
    - Generates follow-up questions and recommendations
    """
    request_id = request.state.request_id
    assessment_id = generate_request_id()
    start_time = time.time()
    
    logger.info(f"Starting assessment {assessment_id}", extra={
        'request_id': request_id,
        'assessment_id': assessment_id,
    })
    
    try:
        # Validate file
        if file.size > settings.max_audio_size_mb * 1024 * 1024:
            raise HTTPException(
                status_code=413,
                detail=f"File too large: {file.size / (1024*1024):.1f}MB (max {settings.max_audio_size_mb}MB)"
            )
        
        if file.content_type not in settings.supported_audio_formats:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid audio format: {file.content_type}. Supported: {settings.supported_audio_formats}"
            )
        
        # Read file
        audio_bytes = await file.read()

        # Skip reprocessing identical audio - return the existing result instead
        import hashlib as _hashlib
        file_hash = _hashlib.sha256(audio_bytes).hexdigest()
        assessment_service = AssessmentService(db)
        existing = assessment_service.get_by_audio_hash(file_hash)
        if existing:
            logger.info(f"Audio already assessed as {existing.id}, returning cached result", extra={
                'request_id': request_id,
            })
            return AssessmentOutput(
                id=existing.id,
                created_at=existing.created_at,
                transcription=existing.transcription,
                symptoms=SymptomExtraction(
                    symptoms=existing.symptoms,
                    severity=existing.severity,
                    duration_days=existing.duration_days,
                    onset=existing.onset_type or "unknown",
                    associated_symptoms=existing.associated_symptoms or [],
                ),
                routing=RoutingDecision(
                    specialty=existing.specialty,
                    confidence=existing.routing_confidence,
                    reasoning=existing.escalation_reasoning or "Cached from prior identical audio",
                    escalation_level=existing.escalation_level,
                    requires_immediate_attention=existing.requires_immediate_attention,
                ),
                agent_questions=existing.agent_questions,
                agent_recommendations=existing.agent_recommendations,
                confidence_in_assessment=existing.overall_confidence,
                processing_latency_ms=existing.total_latency_ms,
                transcription_latency_ms=existing.transcription_latency_ms,
                routing_latency_ms=existing.routing_latency_ms,
            )

        # Stage 1: Transcription
        transcription_start = time.time()
        transcriber = get_transcriber()
        
        try:
            transcription = transcriber.transcribe_from_bytes(
                audio_bytes,
                filename=file.filename,
                language="en",
            )
        except TranscriptionError as e:
            logger.error(f"Transcription failed: {str(e)}", extra={
                'assessment_id': assessment_id,
                'request_id': request_id,
            })
            raise HTTPException(
                status_code=422,
                detail=f"Transcription failed: {str(e)}"
            )
        
        transcription_latency_ms = int((time.time() - transcription_start) * 1000)
        logger.info(f"Transcription completed in {transcription_latency_ms}ms", extra={
            'assessment_id': assessment_id,
            'stage': 'transcription',
        })
        
        # Stage 2: Symptom Extraction
        extraction_start = time.time()
        extractor = get_extractor()
        symptoms = extractor.extract(transcription)
        
        extraction_latency_ms = int((time.time() - extraction_start) * 1000)
        logger.info(f"Extraction completed in {extraction_latency_ms}ms", extra={
            'assessment_id': assessment_id,
            'stage': 'extraction',
            'symptom_count': len(symptoms.symptoms),
        })
        
        # Stage 3: Specialty Routing
        routing_start = time.time()
        router = get_router()
        routing = router.route(symptoms)
        
        routing_latency_ms = int((time.time() - routing_start) * 1000)
        logger.info(f"Routing completed to {routing.specialty} in {routing_latency_ms}ms", extra={
            'assessment_id': assessment_id,
            'stage': 'routing',
            'specialty': routing.specialty,
            'confidence': routing.confidence,
        })
        
        # Stage 4: Agent Response
        agent_start = time.time()
        agent = AgentFactory.get_agent(routing.specialty, use_mock=False)
        questions, recommendations = agent.get_assessment(symptoms, routing)
        
        agent_latency_ms = int((time.time() - agent_start) * 1000)
        logger.info(f"Agent response completed in {agent_latency_ms}ms", extra={
            'assessment_id': assessment_id,
            'stage': 'agent_response',
            'question_count': len(questions),
        })
        
        # Overall latency
        total_latency_ms = int((time.time() - start_time) * 1000)
        
        # Stage 5: Storage
        storage_start = time.time()

        # Create assessment record
        db_assessment = assessment_service.create_assessment(
            audio_file_hash=file_hash,
            audio_size_bytes=len(audio_bytes),
            transcription=transcription,
            symptoms=symptoms.symptoms,
            severity=symptoms.severity,
            specialty=routing.specialty,
            routing_confidence=routing.confidence,
            escalation_level=routing.escalation_level,
            agent_questions=questions,
            agent_recommendations=recommendations,
            overall_confidence=routing.confidence,
            latency_ms=total_latency_ms,
            transcription_latency_ms=transcription_latency_ms,
            extraction_latency_ms=extraction_latency_ms,
            routing_latency_ms=routing_latency_ms,
            agent_response_latency_ms=agent_latency_ms,
            duration_days=symptoms.duration_days,
            onset_type=symptoms.onset,
            requires_immediate_attention=routing.requires_immediate_attention,
        )
        
        storage_latency_ms = int((time.time() - storage_start) * 1000)
        
        # Audit log
        audit_service = AuditService(db)
        audit_service.log_action(
            action="assessment_completed",
            action_type="INFO",
            actor="system",
            assessment_id=db_assessment.id,
            details={
                "specialty": routing.specialty,
                "confidence": routing.confidence,
                "escalation_level": routing.escalation_level,
            },
        )
        
        # Build response
        response = AssessmentOutput(
            id=db_assessment.id,
            created_at=db_assessment.created_at,
            transcription=transcription,
            symptoms=symptoms,
            routing=routing,
            agent_questions=questions,
            agent_recommendations=recommendations,
            confidence_in_assessment=routing.confidence,
            processing_latency_ms=total_latency_ms,
            transcription_latency_ms=transcription_latency_ms,
            routing_latency_ms=routing_latency_ms,
        )
        
        logger.info(f"Assessment {assessment_id} completed successfully in {total_latency_ms}ms", extra={
            'assessment_id': assessment_id,
            'request_id': request_id,
            'total_latency_ms': total_latency_ms,
        })
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Assessment failed: {str(e)}", extra={
            'assessment_id': assessment_id,
            'request_id': request_id,
        }, exc_info=True)
        
        metrics.record_error(
            error_type="assessment_failed",
            error_message=str(e),
            request_id=request_id,
            assessment_id=assessment_id,
        )
        
        raise HTTPException(
            status_code=500,
            detail="Assessment processing failed"
        )

# ============================================================================
# Text-to-Speech
# ============================================================================

@app.post("/speak")
@limiter.limit(f"{settings.rate_limit_per_minute}/minute")
async def speak(request: Request, text: str):
    """Synthesize speech for arbitrary agent text (gTTS by default, ElevenLabs
    if ELEVENLABS_API_KEY is set). Returns audio/mpeg bytes."""
    try:
        audio_bytes = get_synthesizer().synthesize(text)
    except SynthesisError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return Response(content=audio_bytes, media_type="audio/mpeg")


# ============================================================================
# Real-time streaming assessment (WebSocket)
# ============================================================================

@app.websocket("/ws/assess")
async def ws_assess(websocket: WebSocket):
    """
    Real-time voice pipeline over a WebSocket.

    Protocol: client sends raw 16-bit mono PCM audio frames at 16kHz as
    binary messages. The server buffers a rolling window
    (settings.stream_chunk_seconds) and emits partial transcripts as JSON:
        {"type": "partial", "text": "...", "latency_ms": 240}
    After settings.stream_silence_timeout_seconds of no incoming audio, the
    utterance is considered complete: the server runs the full assessment
    pipeline (extraction -> routing -> agent) and emits:
        {"type": "final", "transcription": "...", "specialty": "...",
         "confidence": 0.8, "reply_text": "..."}
    followed by a binary message containing the synthesized MP3 reply.

    Note: this buffers-and-rebatches audio into a batch Whisper call rather
    than true token-streaming ASR (Groq's API doesn't expose the latter) —
    see src/voice/streaming_transcriber.py for details.
    """
    await websocket.accept()
    session = StreamingSession(transcriber=get_transcriber())
    synthesizer = get_synthesizer()

    async def send_partial(result: StreamResult):
        await websocket.send_json({
            "type": "partial", "text": result.text, "latency_ms": result.latency_ms,
        })

    try:
        while True:
            try:
                message = await asyncio.wait_for(
                    websocket.receive(), timeout=settings.stream_silence_timeout_seconds
                )
            except asyncio.TimeoutError:
                message = None

            if message is not None and "bytes" in message and message["bytes"] is not None:
                partial = session.push_frame(message["bytes"])
                if partial is not None:
                    await send_partial(partial)
                continue
            if message is not None and message.get("type") == "websocket.disconnect":
                break

            if session.is_utterance_complete():
                final = session.finalize()
                if final is None or not final.text.strip():
                    continue
                pipeline_result = run_text_pipeline(final.text)
                await websocket.send_json({
                    "type": "final",
                    "transcription": pipeline_result.transcription,
                    "specialty": pipeline_result.specialty,
                    "confidence": pipeline_result.confidence,
                    "escalation_level": pipeline_result.escalation_level,
                    "reply_text": pipeline_result.reply_text,
                })
                try:
                    audio_reply = synthesizer.synthesize(pipeline_result.reply_text)
                    await websocket.send_bytes(audio_reply)
                except SynthesisError as e:
                    logger.warning(f"TTS reply failed: {e}")
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")


@app.get("/assessments/{assessment_id}")
async def get_assessment(
    assessment_id: str,
    db: Session = Depends(get_db),
):
    """Retrieve previous assessment by ID."""
    assessment_service = AssessmentService(db)
    assessment = assessment_service.get_assessment(assessment_id)
    
    if not assessment:
        raise HTTPException(
            status_code=404,
            detail=f"Assessment {assessment_id} not found"
        )
    
    return assessment.to_dict()

# ============================================================================
# Error Handlers
# ============================================================================

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle uncaught exceptions."""
    request_id = getattr(request.state, 'request_id', 'unknown')
    
    logger.error(
        f"Unhandled exception: {str(exc)}",
        extra={'request_id': request_id},
        exc_info=True
    )
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "request_id": request_id,
            "timestamp": datetime.utcnow().isoformat(),
        }
    )

# ============================================================================
# Startup/Shutdown Events
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    logger.info("Starting Medical Voice Agent")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Database: {settings.database_url}")
    
    # Test database connection
    try:
        db = SessionLocal()
        db.execute("SELECT 1")
        db.close()
        logger.info("Database connection successful")
    except Exception as e:
        logger.error(f"Database connection failed: {str(e)}")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("Shutting down Medical Voice Agent")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host=settings.api_host,
        port=settings.api_port,
        log_level=settings.log_level.lower(),
    )
