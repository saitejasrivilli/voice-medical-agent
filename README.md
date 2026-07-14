# Medical Voice Agent

Production-grade medical voice assessment system with specialty routing, LLM-based symptom extraction, and specialty-specific clinical agents.

## Features

- **Real Voice Integration**: Accepts audio uploads (.wav, .mp3, .webm) and transcribes using Groq Whisper API
- **Intelligent Symptom Extraction**: Uses LLM to extract structured medical information from transcriptions
- **Specialty-Specific Routing**: Intelligently routes patients to appropriate medical specialty (Cardiology, Orthopedics, Dermatology, General Triage)
- **Specialty-Specific Agents**: Each specialty has custom logic for follow-up questions and recommendations
- **Production Patterns**: Database persistence, audit logging, observability, rate limiting, error handling
- **API-First Design**: RESTful API with FastAPI, easy integration with frontend/mobile apps

## Architecture

```
User Audio Upload
    ↓
┌─ Stage 1: Transcription (Groq Whisper) → Text
│
├─ Stage 2: Symptom Extraction (LLM) → Structured Data
│
├─ Stage 3: Specialty Routing → Confidence Score + Escalation Level
│
├─ Stage 4: Specialty Agent → Follow-up Questions + Recommendations
│
└─ Stage 5: Database Persistence + Audit Logging
```

## Tech Stack

- **API Framework**: FastAPI
- **Transcription**: Groq Whisper API
- **LLM**: Groq Mixtral (for extraction)
- **Database**: PostgreSQL (production) / SQLite (development)
- **ORM**: SQLAlchemy
- **Container**: Docker
- **Testing**: pytest
- **Monitoring**: Structured JSON logging, metrics collection

## Quick Start

### Prerequisites

- Python 3.11+
- Groq API Key (get from https://console.groq.com)
- PostgreSQL 13+ (optional, SQLite works for dev)

### Installation

1. **Clone and setup**:
```bash
cd voice-medical-agent
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

2. **Configure environment**:
```bash
cp .env.example .env
# Edit .env and add your GROQ_API_KEY
```

3. **Initialize database**:
```bash
python -c "from src.database.models import init_db; from src.config import settings; init_db(settings.database_url)"
```

4. **Run server**:
```bash
python -m uvicorn src.api.main:app --reload
```

Server runs on `http://localhost:8000`

### Using Docker Compose

```bash
# Start all services (app + PostgreSQL)
docker-compose up

# Stop services
docker-compose down
```

## API Endpoints

### POST /assess
Upload audio file for assessment.

**Request**:
```bash
curl -X POST http://localhost:8000/assess \
  -H "Content-Type: multipart/form-data" \
  -F "file=@symptoms.wav"
```

**Response** (200 OK):
```json
{
  "id": "uuid",
  "created_at": "2024-01-15T10:30:00",
  "transcription": "I have chest pain and shortness of breath",
  "symptoms": {
    "symptoms": ["chest pain", "shortness of breath"],
    "severity": "critical",
    "duration_days": null,
    "onset": "sudden"
  },
  "routing": {
    "specialty": "cardiology",
    "confidence": 0.95,
    "escalation_level": "ER",
    "requires_immediate_attention": true
  },
  "agent_questions": [
    "On a scale of 1-10, how severe is your chest pain?",
    "Do you have a history of heart disease?",
    "When did this pain start?"
  ],
  "agent_recommendations": "URGENT - Seek immediate emergency care (911)...",
  "confidence_in_assessment": 0.95,
  "processing_latency_ms": 2850
}
```

### GET /health
Health check endpoint.

**Response**:
```json
{
  "status": "healthy",
  "groq_api_available": true,
  "database_available": true,
  "timestamp": "2024-01-15T10:30:00",
  "version": "1.0.0"
}
```

### GET /metrics
Get aggregated metrics.

**Response**:
```json
{
  "total_assessments": 42,
  "successful_assessments": 40,
  "success_rate": 0.95,
  "avg_latency_ms": 2150,
  "specialty_distribution": {
    "cardiology": 12,
    "orthopedics": 15,
    "dermatology": 10,
    "general_triage": 5
  },
  "timestamp": "2024-01-15T10:30:00"
}
```

### GET /assessments/{assessment_id}
Retrieve previous assessment.

## Configuration

All configuration via environment variables (see `.env.example`):

```bash
# Application
ENVIRONMENT=production
DEBUG=false

# API
API_PORT=8000

# Groq API (REQUIRED)
GROQ_API_KEY=your_key_here

# Database
DATABASE_URL=postgresql://user:pass@localhost/medical_agent

# Rate Limiting
RATE_LIMIT_PER_MINUTE=10

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
```

## Specialty Routing

The system intelligently routes based on symptom keywords and severity:

### Cardiology
- **Keywords**: chest, heart, palpitation, ecg, troponin, arrhythmia, angina
- **Critical → ER**: Severe chest pain, shortness of breath, unstable angina
- **High → Urgent Office**: Moderate chest discomfort with risk factors
- **Low → Monitor Home**: Mild palpitations, stress-related symptoms

### Orthopedics
- **Keywords**: knee, ankle, fracture, sprain, joint, bone, ligament
- **Critical → ER**: Severe fracture, open fracture, neurovascular compromise
- **High → Office**: Significant pain/swelling limiting function
- **Low → Monitor Home**: Minor sprains, mild pain

### Dermatology
- **Keywords**: rash, lesion, skin, itch, mole, dermatitis, eczema, fungal
- **High → Urgent Office**: Signs of infection, spreading rash
- **Low → Office**: Stable rash, cosmetic concerns

## Testing

Run unit tests:

```bash
pytest tests/unit/test_agents.py -v
```

Key test scenarios:

- Chest pain → Cardiology (ER escalation)
- Joint swelling → Orthopedics (Office escalation)
- Rash → Dermatology (Monitor escalation)
- Mixed symptoms → General Triage

## Database Schema

### Assessments Table
Stores all patient assessments with:
- Transcription text
- Extracted symptoms + severity
- Routing decision + confidence
- Agent questions + recommendations
- Performance metrics (latency per stage)
- Audit trail (reviewed_by, notes, timestamp)

Indexes on:
- `created_at` (time-range queries)
- `specialty` (specialty-specific reports)
- `severity` + `escalation_level` (urgent case detection)
- `audio_file_hash` (deduplication)

### Audit Logs Table
Tracks all system actions:
- Assessment creation/routing/review
- Errors and warnings
- User actions (if multi-user)

### Performance Metrics Table
Aggregated metrics for monitoring:
- Success rates
- Latency percentiles (p95, p99)
- Distribution by specialty/severity
- Average confidence scores

## Deployment

### Production Checklist

- [ ] Set `ENVIRONMENT=production`, `DEBUG=false`
- [ ] Use PostgreSQL (not SQLite)
- [ ] Configure proper `LOG_LEVEL` (INFO or WARNING)
- [ ] Set up monitoring/alerting on error logs
- [ ] Configure rate limiting appropriately
- [ ] Set up automated backups for database
- [ ] Use HTTPS in production
- [ ] Implement API authentication if needed
- [ ] Set `CORS_ORIGINS` to your frontend domain only

### Deploy to Railway/Render

1. **Connect GitHub repo**
2. **Set environment variables** (including `GROQ_API_KEY`)
3. **Add PostgreSQL addon**
4. **Deploy** - CI/CD will build Docker image and run

## Observability

### Structured Logging

All logs are JSON-formatted with:
- Timestamp
- Log level (INFO, WARNING, ERROR)
- Component (logger name)
- Request ID (for tracing)
- Assessment ID (if applicable)
- Latency metrics
- Error details with stack traces

**Example**:
```json
{
  "timestamp": "2024-01-15T10:30:00.123",
  "level": "INFO",
  "logger": "src.api.main",
  "message": "Assessment completed successfully",
  "request_id": "uuid-123",
  "assessment_id": "uuid-456",
  "total_latency_ms": 2850,
  "stage": "transcription"
}
```

### Metrics Collection

Automatically tracks:
- Per-stage latency (transcription, extraction, routing, agent)
- Success/failure rates
- Confidence scores
- Specialty distribution
- Escalation distribution

Access via `/metrics` endpoint.

## Error Handling

The system gracefully handles failures:

- **Transcription fails**: Returns error with fallback to text input option
- **Extraction fails**: Falls back to keyword-based extraction
- **Routing fails**: Escalates to general triage
- **Database down**: API returns 500 with request ID for debugging
- **Rate limit exceeded**: Returns 429 with retry-after header

## Security Considerations

- Audio files validated (format, size) before processing
- All patient data stored in database (encrypted at rest if needed)
- Audit logging for compliance (HIPAA acknowledgment in docs)
- Rate limiting to prevent abuse
- CORS configured for cross-origin requests
- Non-root Docker container (security best practice)

## Limitations & Future Work

- **Current**: Keyword + confidence-based routing (not ML-trained)
- **Future**: Train specialty routing on real labeled data
- **Current**: LLM-based extraction (can hallucinate)
- **Future**: Implement validation layer to prevent hallucinations
- **Current**: 3 specialties + general triage
- **Future**: Expand to more specialties (Neurology, Rheumatology, etc.)
- **Current**: No user authentication
- **Future**: Add user/clinic accounts with patient records

## Support

For issues:
1. Check logs: `docker-compose logs app`
2. Health check: `curl http://localhost:8000/health`
3. Test endpoint: `curl -X POST http://localhost:8000/assess -F file=@test.wav`

## License

MIT
