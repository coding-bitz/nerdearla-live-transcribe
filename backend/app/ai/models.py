from typing import Final
from app.config import ALLOWED_MODELS, validate_model_whitelist

# Strictly enforced model constants
TRANSCRIPTION_MODEL: Final[str] = ALLOWED_MODELS["transcription"]
TRANSLATION_MODEL: Final[str] = ALLOWED_MODELS["translation"]
UTILITY_MODEL: Final[str] = ALLOWED_MODELS["utility"]


def assert_transcription_model(model_id: str) -> None:
    validate_model_whitelist("transcription", model_id)


def assert_translation_model(model_id: str) -> None:
    validate_model_whitelist("translation", model_id)


def assert_utility_model(model_id: str) -> None:
    validate_model_whitelist("utility", model_id)
