"""
Shared text-in, response-out assessment pipeline used by the batch /assess
endpoint, the real-time WebSocket handler, and the WebRTC agent — so all
three entry points route through identical extraction/routing/agent logic.
"""

from dataclasses import dataclass

from app.agents.symptom_extractor import LLMBasedExtractor
from app.agents.specialty_router import SpecialtyRouter
from app.agents.factory import AgentFactory
from app.config import settings


@dataclass
class PipelineResult:
    transcription: str
    specialty: str
    confidence: float
    escalation_level: str
    questions: list
    recommendations: list
    reply_text: str


_extractor = None
_router = None


def get_extractor():
    global _extractor
    if _extractor is None:
        _extractor = LLMBasedExtractor(api_key=settings.groq_api_key)
    return _extractor


def get_router():
    global _router
    if _router is None:
        _router = SpecialtyRouter(confidence_threshold=settings.routing_confidence_threshold)
    return _router


def run_text_pipeline(transcription: str) -> PipelineResult:
    """Extract symptoms, route to specialty, and get the agent's spoken reply."""
    symptoms = get_extractor().extract(transcription)
    routing = get_router().route(symptoms)
    agent = AgentFactory.get_agent(routing.specialty, use_mock=False)
    questions, recommendations = agent.get_assessment(symptoms, routing)

    reply_parts = []
    if questions:
        reply_parts.append(questions[0])
    elif recommendations:
        reply_parts.append(recommendations[0])
    reply_text = " ".join(reply_parts) or "Could you tell me more about your symptoms?"

    return PipelineResult(
        transcription=transcription,
        specialty=routing.specialty,
        confidence=routing.confidence,
        escalation_level=routing.escalation_level,
        questions=questions,
        recommendations=recommendations,
        reply_text=reply_text,
    )
