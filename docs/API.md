# API Documentation

## Overview

The Medical Voice Agent API provides medical assessment through voice/audio analysis. Submit an audio file containing patient symptoms, receive specialty routing and clinical recommendations.

## Base URL

```
http://localhost:8000  (Development)
https://api.medicalvoiceagent.com  (Production)
```

## Authentication

Currently no authentication required. In production, implement API key or OAuth2.

## Rate Limiting

- **Per Minute**: 10 requests/minute per IP
- **Per Hour**: 100 requests/hour per IP
- **Response Header**: `X-RateLimit-Remaining`, `X-RateLimit-Reset`

On rate limit:
```
HTTP/1.1 429 Too Many Requests
{
  "error": "Rate limit exceeded",
  "detail": "..."
}
```

## Endpoints

### POST /assess

Upload audio file for medical assessment.

**Request**

```bash
curl -X POST http://localhost:8000/assess \
  -H "Content-Type: multipart/form-data" \
  -F "file=@/path/to/symptoms.wav"
```

**Parameters**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `file` | File | Yes | Audio file (.wav, .mp3, .webm, .m4a) |

**Constraints**

- Max file size: 25 MB
- Supported formats: audio/mpeg, audio/wav, audio/webm
- Duration: Any (typically 15 seconds - 5 minutes for symptoms)

**Success Response** (200 OK)

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "created_at": "2024-01-15T10:30:00Z",
  "transcription": "I have severe chest pain and shortness of breath. It started suddenly about 2 hours ago.",
  "symptoms": {
    "symptoms": ["chest pain", "shortness of breath"],
    "severity": "critical",
    "duration_days": null,
    "onset": "sudden",
    "associated_symptoms": []
  },
  "routing": {
    "specialty": "cardiology",
    "confidence": 0.95,
    "reasoning": "Matched 95% on cardiology symptoms",
    "escalation_level": "ER",
    "requires_immediate_attention": true
  },
  "agent_questions": [
    "On a scale of 1-10, how severe is your chest pain or discomfort? Is it constant or intermittent?",
    "Are you having difficulty breathing at rest or only with exertion? When did this start?",
    "Do you have a history of high blood pressure, diabetes, or high cholesterol?"
  ],
  "agent_recommendations": "URGENT - Seek immediate emergency care (911). You may be experiencing acute coronary syndrome or another life-threatening condition. Do not drive yourself. Call 911 immediately.",
  "confidence_in_assessment": 0.95,
  "processing_latency_ms": 2850,
  "transcription_latency_ms": 1200,
  "routing_latency_ms": 45
}
```

**Error Responses**

```
413 Payload Too Large
{
  "error": "File too large"
}

400 Bad Request
{
  "error": "Invalid audio format"
}

422 Unprocessable Entity
{
  "error": "Transcription failed: [reason]"
}

500 Internal Server Error
{
  "error": "Assessment processing failed",
  "request_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

### GET /assessments/{assessment_id}

Retrieve a previous assessment by ID.

**Request**

```bash
curl http://localhost:8000/assessments/550e8400-e29b-41d4-a716-446655440000
```

**Success Response** (200 OK)

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "created_at": "2024-01-15T10:30:00Z",
  "transcription": "I have severe chest pain...",
  "symptoms": {...},
  "specialty": "cardiology",
  "routing_confidence": 0.95,
  "escalation_level": "ER",
  "agent_questions": [...],
  "agent_recommendations": "...",
  "total_latency_ms": 2850
}
```

**Error Response** (404 Not Found)

```json
{
  "error": "Assessment not found"
}
```

### GET /health

Health check for deployment monitoring.

**Request**

```bash
curl http://localhost:8000/health
```

**Success Response** (200 OK)

```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00Z",
  "groq_api_available": true,
  "database_available": true,
  "version": "1.0.0"
}
```

**Response Fields**

| Field | Type | Meaning |
|-------|------|---------|
| `status` | string | "healthy" or "degraded" |
| `groq_api_available` | bool | Groq API connection OK |
| `database_available` | bool | Database connection OK |
| `timestamp` | datetime | Check time (UTC) |
| `version` | string | API version |

### GET /metrics

Get aggregated performance metrics.

**Request**

```bash
curl http://localhost:8000/metrics
```

**Success Response** (200 OK)

```json
{
  "total_assessments": 42,
  "successful_assessments": 40,
  "success_rate": 0.9524,
  "avg_latency_ms": 2150.5,
  "specialty_distribution": {
    "cardiology": 12,
    "orthopedics": 15,
    "dermatology": 10,
    "general_triage": 5
  },
  "escalation_distribution": {
    "ER": 3,
    "urgent_office": 8,
    "office": 25,
    "monitor_home": 6
  },
  "timestamp": "2024-01-15T10:30:00Z"
}
```

## Examples

### Example 1: Chest Pain (Cardiology, ER)

```bash
# Create audio file (or use existing)
curl -X POST http://localhost:8000/assess \
  -F "file=@chest_pain.wav"
```

**Expected Response**:
- Specialty: Cardiology
- Escalation: ER
- Questions about pain severity, risk factors
- Recommendation: Call 911

### Example 2: Knee Injury (Orthopedics, Office)

```bash
curl -X POST http://localhost:8000/assess \
  -F "file=@knee_injury.wav"
```

**Expected Response**:
- Specialty: Orthopedics
- Escalation: Office
- Questions about mechanism, ROM, swelling
- Recommendation: RICE protocol + appointment

### Example 3: Rash (Dermatology, Office)

```bash
curl -X POST http://localhost:8000/assess \
  -F "file=@rash.wav"
```

**Expected Response**:
- Specialty: Dermatology
- Escalation: Office
- Questions about appearance, duration
- Recommendation: Monitor + dermatology appointment

## Response Structure

### AssessmentOutput

```json
{
  "id": "UUID - Unique assessment ID",
  "created_at": "ISO 8601 timestamp",
  "transcription": "string - Transcribed audio",
  "symptoms": {
    "symptoms": ["list of detected symptoms"],
    "severity": "low|moderate|high|critical",
    "duration_days": "number or null",
    "onset": "sudden|gradual|unknown",
    "associated_symptoms": ["related symptoms"]
  },
  "routing": {
    "specialty": "cardiology|orthopedics|dermatology|general_triage",
    "confidence": "0.0-1.0",
    "reasoning": "string - Why this specialty",
    "escalation_level": "ER|urgent_office|office|monitor_home",
    "requires_immediate_attention": "boolean"
  },
  "agent_questions": ["array of 2-3 follow-up questions"],
  "agent_recommendations": "string - Clinical recommendations",
  "confidence_in_assessment": "0.0-1.0 - Overall assessment confidence",
  "processing_latency_ms": "Total time in milliseconds",
  "transcription_latency_ms": "Stage latency",
  "routing_latency_ms": "Stage latency"
}
```

## Severity Levels

| Level | Description | Examples |
|-------|-------------|----------|
| **Critical** | Life-threatening, immediate care needed | Severe chest pain, difficulty breathing, severe bleeding |
| **High** | Serious but not immediately life-threatening | Severe pain, severe swelling, significant disability |
| **Moderate** | Notable symptoms affecting function | Moderate pain, swelling, discomfort |
| **Low** | Mild symptoms, minimal impact | Slight discomfort, minor symptoms |

## Escalation Levels

| Level | Action | Timeline |
|-------|--------|----------|
| **ER** | Go to emergency room immediately (911) | Immediate |
| **Urgent Office** | See healthcare provider same day | Within 24 hours |
| **Office** | Schedule normal appointment | Within 1-2 weeks |
| **Monitor Home** | Monitor at home, no immediate action needed | As needed |

## Error Handling

All errors follow standard HTTP status codes:

```
200 OK              - Success
400 Bad Request     - Invalid input (bad format, size, etc.)
404 Not Found       - Resource doesn't exist
413 Payload Large   - File too large
422 Unprocessable   - Validation failed (transcription error, etc.)
429 Too Many Reqs   - Rate limit exceeded
500 Server Error    - Internal error (check request_id for debugging)
```

**Error Response Format**

```json
{
  "error": "Short error message",
  "detail": "Detailed explanation (optional)",
  "request_id": "UUID for tracking",
  "timestamp": "ISO 8601 timestamp"
}
```

Use `request_id` to track errors across logs and support tickets.

## Best Practices

### Request Audio

1. **Quality**: Clear audio, minimal background noise
2. **Language**: English (currently supported)
3. **Duration**: 15 seconds - 5 minutes typically
4. **Format**: WAV or MP3 preferred
5. **Content**: Patient describing symptoms clearly

### Good Audio

```
"I have chest pain and shortness of breath. 
The pain started suddenly about 2 hours ago while I was sitting. 
It's a sharp pain that comes and goes. 
I also feel dizzy."
```

### Poor Audio

```
"uh... yeah... so like... my chest... hurts?"
(Mumbled, unclear, lots of pauses)
```

### Handling Responses

```python
# Pseudocode
import requests

response = requests.post(
    "http://localhost:8000/assess",
    files={"file": open("symptoms.wav", "rb")}
)

if response.status_code == 200:
    assessment = response.json()
    
    # Check escalation
    if assessment["routing"]["escalation_level"] == "ER":
        # Show urgent message, provide 911 link
        show_urgent_message("CALL 911")
    
    # Display questions for patient
    for question in assessment["agent_questions"]:
        print(f"? {question}")
    
    # Show recommendations
    print(assessment["agent_recommendations"])
    
    # Store assessment_id for follow-up
    save_assessment_id(assessment["id"])

elif response.status_code == 429:
    # Rate limited
    wait_time = response.headers.get("Retry-After")
    retry_later(wait_time)

elif response.status_code >= 500:
    # Server error
    error = response.json()
    report_error(error["request_id"])
```

## Webhooks (Future)

Future versions may support webhooks for async processing:

```
POST /assess?webhook=https://example.com/callback

Response: {
  "status": "processing",
  "request_id": "UUID",
  "check_status": "https://api.../requests/UUID"
}

Later:
POST https://example.com/callback
{
  "request_id": "UUID",
  "assessment": {...}
}
```

## Support

For API issues:
1. Check `/health` endpoint
2. Verify file format and size
3. Include `request_id` in support tickets
4. Review logs for error details

