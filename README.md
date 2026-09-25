# Nerdearla Live Subtitles

Real-time AI-powered speech captioning, live translation, and session intelligence built for high-concurrency technical conferences like Nerdearla.

Powered by Google Cloud Run and the Google GenAI Enterprise Agent Platform.

---

## 1. Features

1. **Real-time Speech Captioning**: Streaming transcription with interim (live) and final text outputs.
2. **Simultaneous Live Translation**: Speech-to-speech translation extracting translated text subtitles.
3. **Smart Chapters**: Automatic topic detection and chapter generation every ~30 seconds of talk content.
4. **Executive Summary**: Structured post-talk intelligence with key takeaways, topics, and technical depth rating.
5. **Accessibility Enhancements**: Contextual non-speech acoustic cues and punctuation formatting.
6. **Broadcast Production Controls**: Configurable output delay buffer, live pause/resume, and instant emergency broadcast cut.
7. **Strict No-Fallback Architecture**: Zero third-party fallback dependencies (no Whisper, Deepgram, OpenAI) and zero synthetic demo data.

---

## 2. Architecture & Pipeline

```
Browser Microphone
       ↓
Web Audio API AudioWorklet
       ↓
Linear Resampling (16 kHz) & PCM16 Encoding
       ↓
WebSocket (/ws/{session_id})
       ↓
FastAPI Python Backend (Cloud Run)
       ↓
Gemini Live API (Transcribe & Translate) + Flash-Lite (Utility)
       ↓
Browser Live Subtitle Display & Production Controls
```

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for full architectural specifications.

---

## 3. Allowed Models (Strict Whitelist)

The backend enforces a closed whitelist of authorized models:

| Capability | Model Identifier | Interface |
|---|---|---|
| **Live Transcription** | `gemini-3.5-transcribe-live-preview` | Gemini Live API |
| **Live Translation** | `gemini-3.5-live-translate-preview` | Gemini Live API |
| **Smart Chapters** | `gemini-3.5-flash-lite` | GenerateContent API |
| **Executive Summary** | `gemini-3.5-flash-lite` | GenerateContent API |
| **Accessibility** | `gemini-3.5-flash-lite` | GenerateContent API |

Attempts to configure or invoke unauthorized models immediately raise a configuration error.

---

## 4. Authentication (Application Default Credentials)

This project strictly utilizes **Application Default Credentials (ADC)**. Private API keys are **not** required or accepted on Cloud Run.

### Local Development Authentication:
```bash
gcloud auth application-default login
gcloud config set project YOUR_PROJECT_ID
export GOOGLE_CLOUD_PROJECT=YOUR_PROJECT_ID
export GOOGLE_CLOUD_LOCATION=global
```

### Cloud Run Identity:
Cloud Run runs under a dedicated service account (`nerdearla-subtitles`) with minimal IAM permissions:
* `roles/aiplatform.user`

---

## 5. Environment Variables

See `.env.example` for defaults:

```bash
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=global

REDIS_URL=redis://localhost:6379

PORT=8080
ENVIRONMENT=development

FRONTEND_URL=http://localhost:5173

TRANSCRIPTION_MODEL=gemini-3.5-transcribe-live-preview
TRANSLATION_MODEL=gemini-3.5-live-translate-preview
UTILITY_MODEL=gemini-3.5-flash-lite

DEFAULT_SOURCE_LANGUAGE=es-ES
DEFAULT_TRANSLATION_LANGUAGE=es
```

---

## 6. Local Development

### 6.1 Backend
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
```

### 6.2 Frontend
```bash
cd frontend
npm install
npm run dev
```

---

## 7. Docker & Local Services

Run the complete local stack (Backend + Frontend + Redis) via Docker Compose:

```bash
docker compose up --build
```

Verify service endpoints and container health:
* **Frontend**: `http://localhost:5173`
* **Backend API & Health**: `curl http://localhost:8080/health` (HTTP 200 `{"status":"ok"}`)
* **Backend Readiness**: `curl http://localhost:8080/ready` (HTTP 200 when Redis is connected; HTTP 503 if Redis is unavailable)
* **Redis**: `localhost:6379` (healthy)

---

## 8. Deployment to Google Cloud Run

Automated deployment scripts handle project verification, IAM binding, WebSocket timeouts (3600s), and health checks:

```bash
export GOOGLE_CLOUD_PROJECT=your-project-id
export GOOGLE_CLOUD_REGION=us-central1

./deploy/deploy.sh
```

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for full deployment instructions and manual commands.

---

## 9. Audio Pipeline (PCM16 16kHz)

* Compressed container formats (`audio/webm`, `audio/ogg`, `RIFF/WAV`, `MP3`) are **strictly rejected** by the backend audio validator.
* The frontend uses the browser **Web Audio API** and an inline **AudioWorklet** to capture raw Float32 audio, resample to 16,000 Hz, and convert to signed 16-bit linear PCM little-endian integers.
* Audio is transmitted via WebSocket either as JSON base64 frames or binary chunks.

---

## 10. Automated Tests

Run backend unit tests, integration tests, and live ADC verification:

```bash
cd backend
PYTHONPATH=. pytest
```

*Note on Live Google Cloud Tests:* `backend/tests/test_live_gemini.py` performs real API calls against Gemini models when `GOOGLE_CLOUD_PROJECT` and ADC credentials are present; otherwise, it reports an explicit status of `NOT EXECUTED — ADC credentials unavailable or GOOGLE_CLOUD_PROJECT unset` without mock data.

Run frontend type check and production build:

```bash
cd frontend
npm run build
```

---

## 11. Connection States & Error Transparency

### Granular Lifecycle Handshake
The WebSocket connection strictly enforces the following state transitions:
1. `DISCONNECTED`: Initial idle state.
2. `CONNECTING`: Client establishing WebSocket connection to backend.
3. `CONNECTED_BACKEND`: WebSocket established with FastAPI backend.
4. `GEMINI_CONNECTING`: Backend establishing Live API connection to Google GenAI.
5. `GEMINI_READY`: Live session received `setup_complete`. Microphone capture can begin.
6. `STREAMING`: Raw 16kHz mono PCM frames streaming to Gemini.
7. `ERROR`: Explicit error condition reported with structured error payload.
8. `CLOSED`: Clean session shutdown and resource release.

When an AI service encounters an issue, the exact verified provider error is forwarded to the client:

```json
{
  "type": "error",
  "code": "TRANSCRIPTION_ERROR",
  "message": "Detailed verified error message",
  "retryable": false
}
```

The user interface displays:
> *No se pudo generar esta función. [detalle del error]*

Demo or placeholder text is never displayed in place of failed AI calls.

---

## 12. Costs & Pricing

Detailed official pricing rates, calculation formulas, and conference scenario projections are available in [docs/COSTS.md](docs/COSTS.md).

---

## 13. Limitations of Models

* **Preview Status**: `gemini-3.5-transcribe-live-preview` and `gemini-3.5-live-translate-preview` are preview models and subject to Google Cloud regional availability and quota constraints.
* **Network Latency**: Real-time captioning latency depends on network transit time between client, Cloud Run, and Google Agent Platform.
* **Speech-to-Speech Translation**: Live translation runs speech-to-speech internally; textual output is derived from `output_audio_transcription`.

---

## 14. License

Licensed under the Apache License, Version 2.0. See [LICENSE](LICENSE) for the full license text.
