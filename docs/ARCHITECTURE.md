# System Architecture

## Overview

Nerdearla Live Subtitles is a real-time speech captioning, live translation, and session intelligence platform designed for high-concurrency technical conferences. The system is built on Google Cloud Run and leverages the Google GenAI Enterprise Agent Platform.

```
+-----------------------------------------------------------------------------------------+
|                                      Web Browser                                        |
|  +--------------------+         +------------------------+      +--------------------+  |
|  |  AudioWorklet PCM  | ------> |  WebSocket Connection  | <--- |   React UI / State |  |
|  |  (16kHz Mono PCM16)|         |  (Bidirectional JSON)  |      |   (Subtitles/Tabs) |  |
|  +--------------------+         +------------------------+      +--------------------+  |
+---------------------------------------------|-------------------------------------------+
                                              | WS /ws/{session_id}
                                              v
+-----------------------------------------------------------------------------------------+
|                               Cloud Run: Python Backend                                 |
|  +-----------------------------------------------------------------------------------+  |
|  | FastAPI Application & WebSocket Endpoint (/ws/{session_id})                       |  |
|  | - Audio Validator (rejects containers, verifies PCM16 @ 16kHz)                    |  |
|  | - Production Buffer Engine (delay, pause, emergency stop)                         |  |
|  +-----------------------------------------------------------------------------------+  |
|          |                                   |                                   |      |
|          v                                   v                                   v      |
|  +---------------------+           +--------------------+              +-------------+  |
|  | Live Transcription  |           |  Live Translation  |              |   Shared    |  |
|  | gemini-3.5-         |           |  gemini-3.5-live-  |              | Redis State |  |
|  | transcribe-live-    |           |  translate-preview |              | (Sessions/  |  |
|  | preview             |           |  (Speech-to-Speech)|              |  Transcripts|  |
|  +---------------------+           +--------------------+              +-------------+  |
|          |                                   |                                          |
|          +-------------------+---------------+                                          |
|                              v                                                          |
|                    +--------------------+                                               |
|                    |  Utility Services  |                                               |
|                    |  gemini-3.5-       |                                               |
|                    |  flash-lite        |                                               |
|                    |  - Smart Chapters  |                                               |
|                    |  - Executive Summ. |                                               |
|                    |  - Accessibility   |                                               |
|                    +--------------------+                                               |
+-----------------------------------------------------------------------------------------+
```

## Core Architectural Principles

### 1. Zero AI Fallback & Strict Error Propagation
The application strictly forbids third-party fallbacks (no Whisper, Deepgram, OpenAI, AssemblyAI, or synthetic demo transcripts). If an API invocation fails or connectivity drops, the exact verified provider error is structured and forwarded directly to the user interface.

### 2. Closed Model Whitelist
Model identifiers are strictly controlled:
* **Live Transcription**: `gemini-3.5-transcribe-live-preview` (Gemini Live API)
* **Live Translation**: `gemini-3.5-live-translate-preview` (Speech-to-Speech Live API extracting textual output transcription)
* **Utility Intelligence (Chapters, Summary, Accessibility)**: `gemini-3.5-flash-lite` (GenerateContent API with structured JSON output)

### 3. Native AudioWorklet PCM Pipeline
WebM/Opus compressed container formats are not sent to Gemini Live. The browser executes an `AudioWorklet` processor that samples microphone audio, performs linear interpolation downsampling to 16,000 Hz, quantizes Float32 to signed 16-bit little-endian PCM integers, and streams raw PCM frames to the backend.

### 4. Application Default Credentials (ADC)
The backend does not require or accept private API keys in runtime environments. Cloud Run instances execute under a dedicated service account (`nerdearla-subtitles`) authorized with `roles/aiplatform.user`.
