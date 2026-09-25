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


def test_readiness_endpoint_unhealthy_redis(client: TestClient) -> None:
    with patch("app.main.ping_redis", return_value=False):
        response = client.get("/ready")
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "not_ready"
        assert data["redis_connected"] is False


def test_readiness_endpoint_healthy_redis(client: TestClient) -> None:
    with patch("app.main.ping_redis", return_value=True):
        response = client.get("/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
        assert data["redis_connected"] is True
        assert data["models"]["transcription"] == "gemini-3.5-transcribe-live-preview"
        assert data["models"]["translation"] == "gemini-3.5-live-translate-preview"
        assert data["models"]["utility"] == "gemini-3.5-flash-lite"


@pytest.fixture
def auth_headers():
    from app.auth.jwt import create_access_token
    from app.config import settings
    original = settings.auth_jwt_secret
    settings.auth_jwt_secret = "test-secret-that-is-at-least-32-characters-long!"
    token = create_access_token("admin")
    yield {"Authorization": f"Bearer {token}"}
    settings.auth_jwt_secret = original


def test_session_not_found(client: TestClient, auth_headers: dict) -> None:
    response = client.get("/api/sessions/nonexistent-session", headers=auth_headers)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_session_summary_empty_transcript(client: TestClient, auth_headers: dict) -> None:
    await session_manager.get_or_create("empty-sess")
    response = client.post("/api/sessions/empty-sess/summary", headers=auth_headers)
    assert response.status_code == 400


@pytest.fixture
def valid_jwt_token():
    from app.auth.jwt import create_access_token
    from app.config import settings
    original = settings.auth_jwt_secret
    settings.auth_jwt_secret = "test-secret-that-is-at-least-32-characters-long!"
    token = create_access_token("admin")
    yield token
    settings.auth_jwt_secret = original


def test_websocket_rejects_audio_before_ready(client: TestClient, valid_jwt_token: str) -> None:
    with patch("app.websocket.LiveTranscriptionSession") as MockTxSession:
        instance = MockTxSession.return_value
        instance.start = AsyncMock()
        instance.close = AsyncMock()
        instance.send_audio_chunk = AsyncMock()

        async def hanging_events():
            import asyncio
            while True:
                await asyncio.sleep(1)
                yield {}

        instance.receive_events = hanging_events

        with client.websocket_connect("/ws/not-ready-session") as ws:
            # 1. State AUTHENTICATING
            msg0 = json.loads(ws.receive_text())
            assert msg0["type"] == "status" and msg0["status"] == "AUTHENTICATING"

            # 2. Authenticate
            ws.send_text(json.dumps({"type": "auth", "token": valid_jwt_token}))
            assert json.loads(ws.receive_text())["status"] == "AUTHENTICATED"
            assert json.loads(ws.receive_text())["type"] == "auth_success"

            # 3. State GEMINI_CONNECTING
            msg1 = json.loads(ws.receive_text())
            assert msg1["type"] == "status" and msg1["status"] == "GEMINI_CONNECTING"

            # Attempt sending audio before GEMINI_READY
            silence_b64 = base64.b64encode(b"\x00\x00" * 160).decode("ascii")
            ws.send_text(json.dumps({"type": "audio", "data": silence_b64}))

            err = json.loads(ws.receive_text())
            assert err["type"] == "error"
            assert err["code"] == "TRANSCRIPTION_ERROR"
            assert "Waiting for 'GEMINI_READY'" in err["message"]


def test_websocket_audio_format_validation(client: TestClient, valid_jwt_token: str) -> None:
    with patch("app.websocket.LiveTranscriptionSession") as MockTxSession:
        instance = MockTxSession.return_value
        instance.start = AsyncMock()
        instance.close = AsyncMock()
        instance.send_audio_chunk = AsyncMock()

        async def ready_events():
            yield {"type": "ready"}

        instance.receive_events = ready_events

        with client.websocket_connect("/ws/test-ws-session") as ws:
            # Authenticate
            msg0 = json.loads(ws.receive_text())
            assert msg0["type"] == "status" and msg0["status"] == "AUTHENTICATING"
            ws.send_text(json.dumps({"type": "auth", "token": valid_jwt_token}))
            assert json.loads(ws.receive_text())["status"] == "AUTHENTICATED"
            assert json.loads(ws.receive_text())["type"] == "auth_success"

            # Read status frames until GEMINI_READY
            msg1 = json.loads(ws.receive_text())
            assert msg1["type"] == "status" and msg1["status"] == "GEMINI_CONNECTING"
            msg2 = json.loads(ws.receive_text())
            assert msg2["type"] == "status" and msg2["status"] == "GEMINI_READY"
            msg3 = json.loads(ws.receive_text())
            assert msg3["type"] == "ready"

            # Send invalid audio format (odd bytes)
            odd_bytes_b64 = base64.b64encode(b"\x00\x00\x01").decode("ascii")
            ws.send_text(json.dumps({"type": "audio", "data": odd_bytes_b64}))

            msg = ws.receive_text()
            data = json.loads(msg)
            assert data["type"] == "error"
            assert data["code"] == "INVALID_AUDIO_FORMAT"


def test_websocket_valid_audio_forwarded(client: TestClient, valid_jwt_token: str) -> None:
    with patch("app.websocket.LiveTranscriptionSession") as MockTxSession:
        instance = MockTxSession.return_value
        instance.start = AsyncMock()
        instance.close = AsyncMock()
        instance.send_audio_chunk = AsyncMock()

        async def ready_events():
            yield {"type": "ready"}

        instance.receive_events = ready_events

        with client.websocket_connect("/ws/valid-audio-session") as ws:
            # Authenticate
            msg0 = json.loads(ws.receive_text())
            assert msg0["type"] == "status" and msg0["status"] == "AUTHENTICATING"
            ws.send_text(json.dumps({"type": "auth", "token": valid_jwt_token}))
            assert json.loads(ws.receive_text())["status"] == "AUTHENTICATED"
            assert json.loads(ws.receive_text())["type"] == "auth_success"

            # Read status frames until GEMINI_READY
            msg1 = json.loads(ws.receive_text())
            assert msg1["type"] == "status" and msg1["status"] == "GEMINI_CONNECTING"
            msg2 = json.loads(ws.receive_text())
            assert msg2["type"] == "status" and msg2["status"] == "GEMINI_READY"
            msg3 = json.loads(ws.receive_text())
            assert msg3["type"] == "ready"

            # Send 160 samples (320 bytes) of valid PCM16 silence
            silence_b64 = base64.b64encode(b"\x00\x00" * 160).decode("ascii")
            ws.send_text(json.dumps({"type": "audio", "data": silence_b64}))

            # Read STREAMING status transition
            streaming_msg = json.loads(ws.receive_text())
            assert streaming_msg["type"] == "status"
            assert streaming_msg["status"] == "STREAMING"

            # Stop session
            ws.send_text(json.dumps({"type": "stop"}))
            import time
            time.sleep(0.05)

        instance.send_audio_chunk.assert_called_once()
