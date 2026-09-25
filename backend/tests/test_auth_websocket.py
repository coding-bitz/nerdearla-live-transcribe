import json
from unittest.mock import AsyncMock, patch
import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect
from app.auth.jwt import create_access_token
from app.config import settings
from app.main import app

TEST_SECRET = "super-secret-key-that-is-at-least-32-bytes-long!"


@pytest.fixture(autouse=True)
def setup_jwt_settings():
    orig_secret = settings.auth_jwt_secret
    settings.auth_jwt_secret = TEST_SECRET
    yield
    settings.auth_jwt_secret = orig_secret


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_ws_rejects_audio_before_authentication(client: TestClient) -> None:
    with client.websocket_connect("/ws/unauth-session") as ws:
        status_msg = json.loads(ws.receive_text())
        assert status_msg["type"] == "status" and status_msg["status"] == "AUTHENTICATING"

        # Attempt sending audio before auth
        ws.send_bytes(b"\x00\x00" * 160)
        err = json.loads(ws.receive_text())
        assert err["type"] == "error"
        assert err["code"] == "AUTH_REQUIRED"

        # Read error state transition frame
        err_status = json.loads(ws.receive_text())
        assert err_status["type"] == "status" and err_status["status"] == "ERROR"

        # Connection should be closed by server
        with pytest.raises(WebSocketDisconnect):
            ws.receive_text()


def test_ws_rejects_non_auth_text_message(client: TestClient) -> None:
    with client.websocket_connect("/ws/unauth-session-text") as ws:
        status_msg = json.loads(ws.receive_text())
        assert status_msg["status"] == "AUTHENTICATING"

        # Send non-auth message
        ws.send_text(json.dumps({"type": "stop"}))
        err = json.loads(ws.receive_text())
        assert err["type"] == "error"
        assert err["code"] == "AUTH_REQUIRED"

        err_status = json.loads(ws.receive_text())
        assert err_status["status"] == "ERROR"

        with pytest.raises(WebSocketDisconnect):
            ws.receive_text()


def test_ws_rejects_invalid_token(client: TestClient) -> None:
    with client.websocket_connect("/ws/invalid-token-session") as ws:
        status_msg = json.loads(ws.receive_text())
        assert status_msg["status"] == "AUTHENTICATING"

        # Send invalid auth token
        ws.send_text(json.dumps({"type": "auth", "token": "not.a.valid.jwt"}))
        err = json.loads(ws.receive_text())
        assert err["type"] == "error"
        assert err["code"] == "AUTH_INVALID_TOKEN"

        err_status = json.loads(ws.receive_text())
        assert err_status["status"] == "ERROR"

        with pytest.raises(WebSocketDisconnect):
            ws.receive_text()


def test_ws_rejects_expired_token(client: TestClient) -> None:
    expired_token = create_access_token("admin", expires_in_seconds=-10)

    with client.websocket_connect("/ws/expired-token-session") as ws:
        status_msg = json.loads(ws.receive_text())
        assert status_msg["status"] == "AUTHENTICATING"

        # Send expired token
        ws.send_text(json.dumps({"type": "auth", "token": expired_token}))
        err = json.loads(ws.receive_text())
        assert err["type"] == "error"
        assert err["code"] == "AUTH_EXPIRED"

        err_status = json.loads(ws.receive_text())
        assert err_status["status"] == "ERROR"

        with pytest.raises(WebSocketDisconnect):
            ws.receive_text()


def test_ws_valid_auth_starts_gemini_sessions(client: TestClient) -> None:
    valid_token = create_access_token("operator-1")

    with patch("app.websocket.LiveTranscriptionSession") as MockTxSession:
        instance = MockTxSession.return_value
        instance.start = AsyncMock()
        instance.close = AsyncMock()

        async def ready_events():
            yield {"type": "ready"}

        instance.receive_events = ready_events

        with client.websocket_connect("/ws/valid-auth-session") as ws:
            status_msg = json.loads(ws.receive_text())
            assert status_msg["status"] == "AUTHENTICATING"

            # Gemini should NOT be started yet
            assert instance.start.call_count == 0

            # Send valid auth
            ws.send_text(json.dumps({"type": "auth", "token": valid_token}))

            # Authenticated status and success received
            auth_status = json.loads(ws.receive_text())
            assert auth_status["status"] == "AUTHENTICATED"

            auth_success = json.loads(ws.receive_text())
            assert auth_success["type"] == "auth_success"
            assert auth_success["username"] == "operator-1"

            # Transition to GEMINI_CONNECTING
            gemini_connecting = json.loads(ws.receive_text())
            assert gemini_connecting["status"] == "GEMINI_CONNECTING"

            # Only now Gemini start was called!
            assert instance.start.call_count == 1
