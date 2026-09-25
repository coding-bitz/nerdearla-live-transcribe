from typing import Dict, Final
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from app.errors import ConfigError

# Whitelist strictly enforced across all AI services
ALLOWED_MODELS: Final[Dict[str, str]] = {
    "transcription": "gemini-3.5-transcribe-live-preview",
    "translation": "gemini-3.5-live-translate-preview",
    "utility": "gemini-3.5-flash-lite",
}


def validate_model_whitelist(role: str, model_id: str) -> None:
    expected = ALLOWED_MODELS.get(role)
    if expected is None:
        raise ConfigError(f"Unknown AI role '{role}'. Allowed roles: {list(ALLOWED_MODELS.keys())}")
    if model_id != expected:
        raise ConfigError(
            f"Invalid model '{model_id}' for role '{role}'. Strictly required: '{expected}'"
        )


class Settings(BaseSettings):
    google_cloud_project: str = ""
    google_cloud_location: str = "global"

    redis_url: str = "redis://localhost:6379"

    port: int = 8080
    environment: str = "development"

    frontend_url: str = "http://localhost:5173"

    transcription_model: str = ALLOWED_MODELS["transcription"]
    translation_model: str = ALLOWED_MODELS["translation"]
    utility_model: str = ALLOWED_MODELS["utility"]

    default_source_language: str = "es-ES"
    default_translation_language: str = "es"

    # Authentication configuration (stateless single-operator)
    auth_username: str = "admin"
    auth_password_hash: str = ""
    auth_jwt_secret: str = ""
    auth_jwt_expires_seconds: int = 28800
    auth_rate_limit_attempts: int = 5
    auth_rate_limit_window_seconds: int = 300

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("transcription_model")
    @classmethod
    def validate_transcription_model(cls, value: str) -> str:
        if value != ALLOWED_MODELS["transcription"]:
            raise ValueError(
                f"Invalid transcription model '{value}'. Must be '{ALLOWED_MODELS['transcription']}'"
            )
        return value

    @field_validator("translation_model")
    @classmethod
    def validate_translation_model(cls, value: str) -> str:
        if value != ALLOWED_MODELS["translation"]:
            raise ValueError(
                f"Invalid translation model '{value}'. Must be '{ALLOWED_MODELS['translation']}'"
            )
        return value

    @field_validator("utility_model")
    @classmethod
    def validate_utility_model(cls, value: str) -> str:
        if value != ALLOWED_MODELS["utility"]:
            raise ValueError(
                f"Invalid utility model '{value}'. Must be '{ALLOWED_MODELS['utility']}'"
            )
        return value


settings = Settings()
