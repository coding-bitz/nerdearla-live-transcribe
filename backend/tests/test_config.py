import pytest
from pydantic import ValidationError
from app.config import ALLOWED_MODELS, Settings, validate_model_whitelist
from app.errors import ConfigError


def test_default_models_match_whitelist() -> None:
    settings = Settings()
    assert settings.transcription_model == "gemini-3.5-transcribe-live-preview"
    assert settings.translation_model == "gemini-3.5-live-translate-preview"
    assert settings.utility_model == "gemini-3.5-flash-lite"
    assert settings.transcription_model == ALLOWED_MODELS["transcription"]
    assert settings.translation_model == ALLOWED_MODELS["translation"]
    assert settings.utility_model == ALLOWED_MODELS["utility"]


def test_reject_unauthorized_transcription_model() -> None:
    with pytest.raises(ValidationError):
        Settings(transcription_model="gemini-2.0-flash-exp")


def test_reject_unauthorized_translation_model() -> None:
    with pytest.raises(ValidationError):
        Settings(translation_model="gemini-1.5-pro")


def test_reject_unauthorized_utility_model() -> None:
    with pytest.raises(ValidationError):
        Settings(utility_model="gemini-1.5-flash")


def test_validate_model_whitelist_success() -> None:
    validate_model_whitelist("transcription", "gemini-3.5-transcribe-live-preview")
    validate_model_whitelist("translation", "gemini-3.5-live-translate-preview")
    validate_model_whitelist("utility", "gemini-3.5-flash-lite")


def test_validate_model_whitelist_failure() -> None:
    with pytest.raises(ConfigError):
        validate_model_whitelist("transcription", "whisper-large")

    with pytest.raises(ConfigError):
        validate_model_whitelist("unknown_role", "gemini-3.5-flash-lite")
