# Architecture Documentation

## System Design

### High-Level Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    User/Client                              │
│         (Mobile App / Web / Third-party API)                │
└────────────────────┬────────────────────────────────────────┘
                     │
                     │ Audio File Upload
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Server                           │
│  (Rate Limiting, Validation, Error Handling)                │
└────────┬──────────┬──────────┬──────────┬──────────┬────────┘
         │          │          │          │          │
         ▼          ▼          ▼          ▼          ▼
    Transcriber  Extractor  Router    Agents     Storage
    (Groq API)  (LLM-based) (Rules)  (Logic)    (Database)
         │          │          │          │          │
         └──────────┴──────────┴──────────┴──────────┘
                     │
                     ▼
         ┌───────────────────────┐
         │   Response + Logs     │
         │   (Assessment + Q&A)  │
         └───────────────────────┘
```

### Component Breakdown

#### 1. **Transcriber** (`app/services/transcriber.py`)
- **Purpose**: Convert audio to text
- **Implementation**: Groq Whisper API
- **Key Features**:
  - File validation (format, size)
  - File hash calculation for deduplication
  - Graceful error handling
  - Fallback to text input on failure
- **Why Groq**: Free tier, good accuracy, fast latency
- **Fallback**: MockTranscriber for testing without API calls

#### 2. **Symptom Extractor** (`app/agents/symptom_extractor.py`)
- **Purpose**: Extract structured medical data from transcript
- **Implementation**: LLM-based (Groq Mixtral) with keyword fallback
- **Output**: `SymptomExtraction` with:
  - List of symptoms (1-10)
  - Severity level (low/moderate/high/critical)
  - Duration (if mentioned)
  - Onset type (sudden/gradual)
- **Error Handling**:
  - If LLM extraction fails → fallback to keyword matching
  - Validates output against constraints
- **Why Two-Tier**: LLM better for medical language, keyword fallback for reliability

#### 3. **Specialty Router** (`app/agents/specialty_router.py`)
- **Purpose**: Route to appropriate medical specialty
- **Implementation**: Keyword matching with confidence scoring
- **Logic**:
  1. Calculate confidence score for each specialty
  2. Find best match
  3. If confidence < threshold (0.65) → route to general triage
  4. Determine escalation level based on specialty + severity
- **Specialties**:
  - Cardiology (chest/heart symptoms)
  - Orthopedics (joint/bone symptoms)
  - Dermatology (skin symptoms)
  - General Triage (unclear/mixed)
- **Why Rules-Based**: Deterministic, debuggable, no false positives
- **Why Not ML**: Would require labeled training data; rules sufficient for MVP

#### 4. **Specialty Agents** (`app/agents/*_agent.py`)
- **Purpose**: Generate specialty-specific follow-up questions + recommendations
- **Structure**: Base class + 4 specialty implementations
- **Cardiology Agent**:
  - Questions focus on severity, risk factors, triggers
  - Escalation: ER if severe chest pain/SOB, urgent office if moderate
  - Recommendations: Specific cardiac guidelines
- **Orthopedics Agent**:
  - Questions focus on mechanism, ROM, swelling
  - Escalation: ER if severe fracture, office for sprains
  - Recommendations: RICE protocol + specialist referral
- **Dermatology Agent**:
  - Questions focus on appearance, distribution, triggers
  - Escalation: Urgent office if infection suspected
  - Recommendations: Skin care + monitoring
- **General Triage Agent**:
  - Generic questions to understand impact
  - Routes to primary care for proper evaluation
- **Why Specialty-Specific**: Ensures relevant follow-up, improves user experience

#### 5. **Database Layer** (`app/database/`)
- **Models** (`models.py`):
  - `Assessment`: Main assessment records
  - `AuditLog`: Compliance/debugging trail
  - `PerformanceMetrics`: Aggregated metrics
- **Service** (`service.py`):
  - `AssessmentService`: CRUD + queries
  - `AuditService`: Logging actions
  - `MetricsService`: Metric aggregation
- **Why Layered**: Separates ORM from business logic, testable, maintainable

#### 6. **API** (`app/main.py`)
- **Framework**: FastAPI (modern, fast, auto-docs)
- **Endpoints**:
  - `POST /assess`: Main endpoint
  - `GET /health`: Liveness check
  - `GET /metrics`: Metrics dashboard
  - `GET /assessments/{id}`: Retrieve assessment
- **Middleware**:
  - CORS: Cross-origin requests
  - Rate Limiting: 10/min, 100/hour per IP
  - Request tracking: Unique request IDs
  - Error handling: Graceful failures
- **Why FastAPI**: Type safety, auto-validation, built-in OpenAPI docs, excellent performance

#### 7. **Observability** (`app/observability/`)
- **Logging**: JSON structured logging with request tracking
- **Metrics**: Per-stage latency, success rates, distributions
- **Why Important**: Production debugging, monitoring, alerting

## Data Flow

### Successful Assessment Path

```
1. User uploads audio.wav
   ↓
2. FastAPI validates file
   ├─ Check format (audio/wav)
   ├─ Check size (< 25MB)
   └─ Calculate SHA256 hash
   ↓
3. Transcriber processes
   ├─ Call Groq Whisper API
   ├─ Return text transcript
   └─ Record latency: ~500-1500ms
   ↓
4. Symptom Extractor processes
   ├─ Call Groq LLM with prompt
   ├─ Parse JSON response
   ├─ Validate against constraints
   └─ Record latency: ~800-1200ms
   ↓
5. Specialty Router processes
   ├─ Calculate specialty scores
   ├─ Determine escalation level
   └─ Record latency: ~50ms
   ↓
6. Get Appropriate Agent
   ├─ Cardiology / Orthopedics / Dermatology / Triage
   ├─ Generate 2-3 follow-up questions
   ├─ Generate recommendations
   └─ Record latency: ~100ms
   ↓
7. Store in Database
   ├─ Create Assessment record
   ├─ Log audit entry
   ├─ Update metrics
   └─ Record latency: ~100-200ms
   ↓
8. Return Response (total ~2-3.5s)
   └─ Assessment ID, transcription, routing, Q&A, metrics
```

### Error Handling Path

```
Transcription fails
  └─ Try to recover with keyword extraction
  └─ If still fails: Return error, ask for text input

Extraction fails
  └─ Fall back to keyword-based extraction
  └─ Continue with degraded quality

Routing fails
  └─ Default to general triage
  └─ Log error for debugging

Database fails
  └─ Return 500 error with request ID
  └─ User can reference for support
```

## Database Schema Design

### Assessments Table

| Column | Type | Purpose | Index |
|--------|------|---------|-------|
| `id` | UUID | Primary key | ✓ |
| `created_at` | DateTime | Creation time | ✓ (with specialty) |
| `audio_file_hash` | String | Deduplication | ✓ |
| `transcription` | Text | Patient description | |
| `symptoms` | JSON | Extracted symptoms | |
| `severity` | String | Critical/High/Moderate/Low | ✓ |
| `specialty` | String | Routed specialty | ✓ |
| `routing_confidence` | Float | 0.0-1.0 confidence | |
| `escalation_level` | String | ER/Urgent/Office/Monitor | ✓ |
| `agent_questions` | JSON | Follow-up questions | |
| `agent_recommendations` | Text | Clinical recommendations | |
| `overall_confidence` | Float | Assessment confidence | |
| `transcription_latency_ms` | Int | Stage latency | |
| `routing_latency_ms` | Int | Stage latency | |
| `agent_response_latency_ms` | Int | Stage latency | |
| `total_latency_ms` | Int | Total processing time | |
| `is_reviewed` | Boolean | Clinical review flag | ✓ |
| `clinical_reviewer_id` | String | Who reviewed | |
| `reviewed_at` | DateTime | When reviewed | |

**Indexes**:
- `(created_at, specialty)`: Time-range + specialty queries
- `(severity, escalation_level)`: Finding urgent cases
- `(audio_file_hash)`: Deduplication
- `(is_reviewed)`: Finding unreviewed cases
- `(requires_immediate_attention)`: Escalation tracking

### Audit Logs Table

Tracks all system actions for compliance:
- Assessment created
- Routed to specialty
- Clinical review completed
- Errors encountered

Indexed on `created_at` and `assessment_id` for traceability.

## Configuration Management

All configuration via environment variables using Pydantic Settings:

```python
settings = Settings()
```

Benefits:
- No hardcoded values
- 12-factor app compliance
- Different configs per environment (dev/staging/prod)
- Secrets management (API keys via .env)

## Deployment Strategies

### Local Development
```bash
# SQLite database, mock services or real Groq API
python -m uvicorn app.main:app --reload
```

### Docker Local
```bash
# PostgreSQL + app in containers
docker-compose up
```

### Production (Railway/Render)
```
Environment: production
Database: PostgreSQL
Logging: JSON to stdout (collected by platform)
Secrets: Managed by platform (GROQ_API_KEY, DATABASE_URL)
```

## Scalability Considerations

### Current (Single Instance)
- SQLite/PostgreSQL: 1000s assessments/day
- Groq API: 7k tokens/min free tier (sufficient for medical text)
- Memory: ~200MB (Python process)
- CPU: Low (mostly I/O waiting)

### To Scale to Millions/Day:
1. **Database**: PostgreSQL with read replicas, archival for old data
2. **API**: Load balancer + multiple app instances (Kubernetes)
3. **Cache**: Redis for assessment retrieval, config caching
4. **Async**: Move heavy tasks (LLM calls) to async queue (Celery)
5. **LLM**: If hitting rate limits, use cheaper model or cache responses
6. **Monitoring**: Prometheus metrics + Grafana dashboards

## Security & Compliance

### Current
- File validation before processing
- Rate limiting (prevent abuse)
- Audit logging (HIPAA readiness)
- Error messages don't leak sensitive info
- Non-root Docker container
- Structured logging (no PII in logs)

### Production Recommendations
- Enable database encryption at rest
- Use HTTPS everywhere
- Implement API authentication (OAuth2/JWT)
- Limit CORS to specific domains
- Set up WAF (Web Application Firewall)
- Regular security audits
- HIPAA Business Associate Agreement if handling real patient data

## Testing Strategy

### Unit Tests (`tests/unit/`)
- Test each component independently
- Mock external dependencies (Groq API)
- Test error handling paths
- Cover specialty routing logic
- Verify agent outputs

### Integration Tests (`tests/integration/`)
- End-to-end assessment flow
- Database persistence
- Error scenarios

### Test Data
- Real medical scenarios (chest pain, knee injury, rash)
- Edge cases (mixed symptoms, unclear cases)
- Error conditions (malformed audio, API failures)

## Monitoring & Alerting

### Key Metrics
- Latency per stage (p50, p95, p99)
- Success rate (% assessments completed)
- Error rate by type (transcription, extraction, routing)
- Specialty distribution (are we routing correctly?)
- Average confidence scores

### Alert Thresholds
- Error rate > 5%
- p95 latency > 5000ms
- Database unavailable > 1 minute
- Groq API unavailable

### Dashboards
- Real-time assessment volume
- Latency trends
- Error trends
- Specialty heatmap

## Maintenance & Ops

### Daily
- Monitor logs for errors
- Check health endpoint
- Verify database backups

### Weekly
- Review metrics
- Check disk usage
- Update dependencies

### Monthly
- Analyze routing accuracy (compare to gold standard)
- Capacity planning (growth rate)
- Security review

## Future Architecture Decisions

### ML-Based Routing
- Collect labeled training data (specialty + confidence)
- Train logistic regression model
- Integrate into router
- Monitor accuracy vs. rules-based

### Multi-Turn Conversations
- Store conversation history
- LLM-based follow-up logic
- More personalized recommendations

### Integrations
- EHR systems (export assessments)
- Scheduling systems (auto-book appointments)
- Messaging (SMS/WhatsApp for results)

### Specialization
- Add more specialties (Neurology, Rheumatology, etc.)
- Develop domain-specific agents per specialty
- Clinical decision support (evidence-based recommendations)

