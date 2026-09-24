from typing import Any, Dict


class AppError(Exception):
    """Base application exception with standardized error structure."""

    def __init__(self, code: str, message: str, retryable: bool = False) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.retryable = retryable

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "error",
            "code": self.code,
            "message": self.message,
            "retryable": self.retryable,
        }


class ConfigError(AppError):
    def __init__(self, message: str, retryable: bool = False) -> None:
        super().__init__("CONFIG_ERROR", message, retryable)


class AuthError(AppError):
    def __init__(self, message: str, retryable: bool = False) -> None:
        super().__init__("AUTH_ERROR", message, retryable)


class AIServiceError(AppError):
    def __init__(self, message: str, retryable: bool = False) -> None:
        super().__init__("AI_SERVICE_ERROR", message, retryable)


class TranscriptionError(AppError):
    def __init__(self, message: str, retryable: bool = False) -> None:
        super().__init__("TRANSCRIPTION_ERROR", message, retryable)


class TranslationError(AppError):
    def __init__(self, message: str, retryable: bool = False) -> None:
        super().__init__("TRANSLATION_ERROR", message, retryable)


class ChapterError(AppError):
    def __init__(self, message: str, retryable: bool = False) -> None:
        super().__init__("CHAPTER_ERROR", message, retryable)


class SummaryError(AppError):
    def __init__(self, message: str, retryable: bool = False) -> None:
        super().__init__("SUMMARY_ERROR", message, retryable)


class AccessibilityError(AppError):
    def __init__(self, message: str, retryable: bool = False) -> None:
        super().__init__("ACCESSIBILITY_ERROR", message, retryable)


class InvalidAudioFormatError(AppError):
    def __init__(self, message: str = "Expected mono PCM16 at 16 kHz") -> None:
        super().__init__("INVALID_AUDIO_FORMAT", message, retryable=False)


class SessionError(AppError):
    def __init__(self, message: str, retryable: bool = False) -> None:
        super().__init__("SESSION_ERROR", message, retryable)


class WebSocketError(AppError):
    def __init__(self, message: str, retryable: bool = False) -> None:
        super().__init__("WEBSOCKET_ERROR", message, retryable)


def format_error_payload(code: str, message: str, retryable: bool = False) -> Dict[str, Any]:
    return {
        "type": "error",
        "code": code,
        "message": message,
        "retryable": retryable,
    }
