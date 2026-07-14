"""
Core enumerations and constants for medical specialties, severity levels, and escalation.
"""

from enum import Enum


class Severity(str, Enum):
    """Patient symptom severity levels."""
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


class Specialty(str, Enum):
    """Medical specialties handled by the system."""
    CARDIOLOGY = "cardiology"
    ORTHOPEDICS = "orthopedics"
    DERMATOLOGY = "dermatology"
    GENERAL_TRIAGE = "general_triage"


class EscalationLevel(str, Enum):
    """Patient escalation levels."""
    MONITOR_HOME = "monitor_home"
    OFFICE = "office"
    URGENT_OFFICE = "urgent_office"
    ER = "ER"


class ProcessingStage(str, Enum):
    """Stages in the assessment pipeline."""
    TRANSCRIPTION = "transcription"
    EXTRACTION = "extraction"
    ROUTING = "routing"
    AGENT_RESPONSE = "agent_response"
    STORAGE = "storage"


# Medical thresholds and rules
CONFIDENCE_THRESHOLD = 0.65  # Route to general triage if below this
MAX_SYMPTOMS = 10
MIN_SYMPTOMS = 1
DEFAULT_TIMEOUT_SECONDS = 30
MAX_AUDIO_SIZE_MB = 25
ASSESSMENT_RETENTION_DAYS = 90

# Specialty-specific keywords for routing
SPECIALTY_KEYWORDS = {
    Specialty.CARDIOLOGY: [
        "chest", "heart", "palpitation", "ecg", "troponin", "arrhythmia",
        "angina", "cardiac", "coronary", "myocardial", "bp", "blood pressure"
    ],
    Specialty.ORTHOPEDICS: [
        "knee", "ankle", "fracture", "sprain", "xray", "rom", "mobility",
        "joint", "bone", "ligament", "tendon", "orthopedic", "physical therapy"
    ],
    Specialty.DERMATOLOGY: [
        "rash", "lesion", "skin", "itch", "mole", "dermatitis", "eczema",
        "psoriasis", "acne", "fungal", "wart", "nevus"
    ],
}

# Cardiology critical symptoms
CARDIOLOGY_CRITICAL = [
    "severe chest pain", "chest pain with shortness of breath", "acute myocardial",
    "unstable angina", "aortic dissection"
]

# Orthopedics critical symptoms
ORTHOPEDICS_CRITICAL = [
    "severe fracture", "open fracture", "neurovascular compromise"
]

# Dermatology critical symptoms
DERMATOLOGY_CRITICAL = [
    "severe infection", "spreading rash", "anaphylaxis", "stevens johnson"
]
