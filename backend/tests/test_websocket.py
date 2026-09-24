import base64
import json
from unittest.mock import AsyncMock, patch
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.sessions import session_manager


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_health_endpoint(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readiness_endpoint(client: TestClient) -> None:
    response = client.get("/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert "models" in data
    assert data["models"]["transcription"] == "gemini-3.5-transcribe-live-preview"
    assert data["models"]["translation"] == "gemini-3.5-live-translate-preview"
    assert data["models"]["utility"] == "gemini-3.5-flash-lite"


def test_session_not_found(client: TestClient) -> None:
    response = client.get("/api/sessions/nonexistent-session")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_session_summary_empty_transcript(client: TestClient) -> None:
    await session_manager.get_or_create("empty-sess")
    response = client.post("/api/sessions/empty-sess/summary")
    assert response.status_code == 400


def test_websocket_audio_format_validation(client: TestClient) -> None:
    with patch("app.websocket.LiveTranscriptionSession") as MockTxSession:
        instance = MockTxSession.return_value
        instance.start = AsyncMock()
        instance.close = AsyncMock()
        instance.send_audio_chunk = AsyncMock()

        async def empty_events():
            if False:
                yield {}

        instance.receive_events = empty_events

        with client.websocket_connect("/ws/test-ws-session") as ws:
            # Send invalid audio format (odd bytes)
            odd_bytes_b64 = base64.b64encode(b"\x00\x00\x01").decode("ascii")
            ws.send_text(json.dumps({"type": "audio", "data": odd_bytes_b64}))

            msg = ws.receive_text()
            data = json.loads(msg)
            assert data["type"] == "error"
            assert data["code"] == "INVALID_AUDIO_FORMAT"


def test_websocket_valid_audio_forwarded(client: TestClient) -> None:
    with patch("app.websocket.LiveTranscriptionSession") as MockTxSession:
        instance = MockTxSession.return_value
        instance.start = AsyncMock()
        instance.close = AsyncMock()
        instance.send_audio_chunk = AsyncMock()

        async def empty_events():
            if False:
                yield {}

        instance.receive_events = empty_events

        with client.websocket_connect("/ws/valid-audio-session") as ws:
            # Send 160 samples (320 bytes) of valid PCM16 silence
            silence_b64 = base64.b64encode(b"\x00\x00" * 160).decode("ascii")
            ws.send_text(json.dumps({"type": "audio", "data": silence_b64}))

            import time
            time.sleep(0.1)

            # Stop session
            ws.send_text(json.dumps({"type": "stop"}))
            time.sleep(0.05)

        instance.send_audio_chunk.assert_called_once()
