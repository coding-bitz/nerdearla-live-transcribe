# API Specification

## HTTP REST Endpoints

### 1. Health Check
```http
GET /health
```
**Response:**
```json
{
  "status": "ok"
}
```

### 2. Readiness Check
```http
GET /ready
```
**Response:**
```json
{
  "status": "ready",
  "models": {
    "transcription": "gemini-3.5-transcribe-live-preview",
    "translation": "gemini-3.5-live-translate-preview",
    "utility": "gemini-3.5-flash-lite"
  },
  "redis_connected": true,
  "environment": "production"
}
```

### 3. Retrieve Session
```http
GET /api/sessions/{session_id}
```
**Response:**
```json
{
  "session_id": "nerdearla-room-1",
  "created_at": 1710000000000,
  "status": "active",
  "source_language": "es-ES",
  "translation_enabled": false,
  "target_language": "es",
  "final_transcripts": [
    {
      "text": "Bienvenidos a Nerdearla.",
      "timestamp": 1710000001000
    }
  ],
  "chapters": [
    {
      "title": "Apertura y Bienvenida",
      "timestamp": 1710000030000
    }
  ],
  "summary": null,
  "chunk_count": 42
}
```

### 4. Generate Session Summary
```http
POST /api/sessions/{session_id}/summary
```
**Response:**
```json
{
  "title": "Arquitecturas de Audio en Tiempo Real",
  "summary": "Resumen técnico de la conferencia...",
  "keyTakeaways": [
    "Usar PCM16 a 16kHz directamente desde el navegador.",
    "Configurar credenciales mediante ADC en Cloud Run."
  ],
  "resources": [],
  "technicalLevel": "intermediate",
  "topics": ["Cloud Run", "Gemini Live API", "Web Audio"],
  "hashtags": ["#Nerdearla", "#CloudRun", "#Gemini"],
  "estimatedReadingTime": "3 min",
  "chapters": [
    {
      "title": "Apertura",
      "summary": "Presentación inicial del problema."
    }
  ]
}
```

### 5. Enhance Subtitle for Accessibility
```http
POST /api/sessions/{session_id}/accessibility
Content-Type: application/json

{
  "text": "muchas gracias por los aplausos",
  "audio_features": {
    "volume_rms": 0.42
  }
}
```
**Response:**
```json
{
  "enhancedText": "¡Muchas gracias por los aplausos!",
  "soundDescriptions": ["[applause]"],
  "speakerTone": "enthusiastic"
}
```

---

## WebSocket Protocol

**Endpoint:**
```text
ws://<HOST>/ws/{session_id}?source_language=es-ES&translate=false&target_language=es
```

### Client -> Server Messages

#### Stream Audio Chunk (JSON Base64)
```json
{
  "type": "audio",
  "data": "<base64 encoded 16-bit linear PCM at 16000Hz mono>"
}
```
*Note: Direct binary WebSocket frames carrying raw PCM16 bytes are also accepted.*

#### Stop Session
```json
{
  "type": "stop"
}
```

#### Dynamically Enable Live Translation
```json
{
  "type": "start_translation",
  "target_language": "en"
}
```

#### Disable Live Translation
```json
{
  "type": "stop_translation"
}
```

#### Request Live Executive Summary
```json
{
  "type": "request_summary"
}
```

#### Request Accessibility Enhancement
```json
{
  "type": "request_accessibility",
  "text": "Texto del subtitulo a formatear"
}
```

### Server -> Client Messages

#### Session Ready
```json
{
  "type": "ready",
  "sessionId": "nerdearla-room-1"
}
```

#### Interim Transcription
```json
{
  "type": "transcription",
  "subtype": "interim",
  "text": "bienvenidos a",
  "timestamp": 1710000001200
}
```

#### Final Transcription
```json
{
  "type": "transcription",
  "subtype": "final",
  "text": "Bienvenidos a Nerdearla 2026.",
  "timestamp": 1710000002500
}
```

#### Live Translation
```json
{
  "type": "translation",
  "subtype": "translation",
  "text": "Welcome to Nerdearla 2026.",
  "timestamp": 1710000002800
}
```

#### Smart Chapter Detected
```json
{
  "type": "chapter",
  "chapter": {
    "title": "Arquitectura del Pipeline",
    "timestamp": 1710000030000
  }
}
```

#### Error Message
```json
{
  "type": "error",
  "code": "INVALID_AUDIO_FORMAT",
  "message": "Expected mono PCM16 at 16 kHz, received containerized audio",
  "retryable": false
}
```
