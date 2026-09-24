from app.config import ALLOWED_MODELS
from app.errors import (
    AIServiceError,
    AccessibilityError,
    ChapterError,
    ConfigError,
    InvalidAudioFormatError,
    SessionError,
    SummaryError,
    TranscriptionError,
    TranslationError,
    WebSocketError,
    format_error_payload,
)


def test_allowed_models_exact_whitelist() -> None:
    expected_models = {
        "transcription": "gemini-3.5-transcribe-live-preview",
        "translation": "gemini-3.5-live-translate-preview",
        "utility": "gemini-3.5-flash-lite",
    }
    assert ALLOWED_MODELS == expected_models


def test_error_to_dict_structure() -> None:
    err = AIServiceError("Service temporarily unavailable", retryable=True)
    payload = err.to_dict()
    assert payload == {
        "type": "error",
        "code": "AI_SERVICE_ERROR",
        "message": "Service temporarily unavailable",
        "retryable": True,
    }


def test_invalid_audio_format_error_payload() -> None:
    err = InvalidAudioFormatError()
    assert err.code == "INVALID_AUDIO_FORMAT"
    assert err.message == "Expected mono PCM16 at 16 kHz"
    assert err.retryable is False


def test_format_error_payload_helper() -> None:
    payload = format_error_payload("TRANSCRIPTION_ERROR", "Stream closed unexpectedly")
    assert payload == {
        "type": "error",
        "code": "TRANSCRIPTION_ERROR",
        "message": "Stream closed unexpectedly",
        "retryable": False,
    }


def test_error_classes_codes() -> None:
    assert TranscriptionError("msg").code == "TRANSCRIPTION_ERROR"
    assert TranslationError("msg").code == "TRANSLATION_ERROR"
    assert ChapterError("msg").code == "CHAPTER_ERROR"
    assert SummaryError("msg").code == "SUMMARY_ERROR"
    assert AccessibilityError("msg").code == "ACCESSIBILITY_ERROR"
    assert SessionError("msg").code == "SESSION_ERROR"
    assert WebSocketError("msg").code == "WEBSOCKET_ERROR"
    assert ConfigError("msg").code == "CONFIG_ERROR"
