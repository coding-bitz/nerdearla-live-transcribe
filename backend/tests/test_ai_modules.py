import pytest
from app.ai.accessibility import AccessibilityEnhancementSchema, enhance_for_accessibility
from app.ai.chapters import ChapterDetectionSchema, detect_chapter_change
from app.ai.models import (
    TRANSCRIPTION_MODEL,
    TRANSLATION_MODEL,
    UTILITY_MODEL,
    assert_transcription_model,
    assert_translation_model,
    assert_utility_model,
)
from app.ai.summary import ExecutiveSummarySchema, generate_executive_summary
from app.ai.transcription import LiveTranscriptionSession
from app.ai.translation import LiveTranslationSession
from app.errors import AccessibilityError, ConfigError, SummaryError, TranscriptionError, TranslationError


def test_ai_model_whitelist_assertions() -> None:
    assert_transcription_model(TRANSCRIPTION_MODEL)
    assert_translation_model(TRANSLATION_MODEL)
    assert_utility_model(UTILITY_MODEL)

    with pytest.raises(ConfigError):
        assert_transcription_model("gemini-2.0-flash-exp")

    with pytest.raises(ConfigError):
        assert_translation_model("gemini-1.5-flash")

    with pytest.raises(ConfigError):
        assert_utility_model("whisper-large")


@pytest.mark.asyncio
async def test_chapter_detection_empty_input() -> None:
    result = await detect_chapter_change([])
    assert result is None


def test_chapter_detection_schema() -> None:
    valid = ChapterDetectionSchema(chapterChange=True, title="Cloud Run Deployments")
    assert valid.chapterChange is True
    assert valid.title == "Cloud Run Deployments"


@pytest.mark.asyncio
async def test_summary_empty_transcript_fails() -> None:
    with pytest.raises(SummaryError, match="empty transcript"):
        await generate_executive_summary([])


def test_summary_schema_validation() -> None:
    payload = {
        "title": "Scaling Live Audio on Cloud Run",
        "summary": "This talk covers architecture and Web Audio streaming.",
        "keyTakeaways": ["Use PCM16", "Configure ADC properly"],
        "resources": [],
        "technicalLevel": "intermediate",
        "topics": ["Cloud Run", "Web Audio API"],
        "hashtags": ["#CloudRun", "#Gemini"],
        "estimatedReadingTime": "2 min",
        "chapters": [{"title": "Introduction", "summary": "Opening remarks"}],
    }
    schema = ExecutiveSummarySchema(**payload)
    assert schema.technicalLevel == "intermediate"
    assert schema.resources == []


@pytest.mark.asyncio
async def test_accessibility_empty_text_fails() -> None:
    with pytest.raises(AccessibilityError, match="empty subtitle"):
        await enhance_for_accessibility("   ")


def test_accessibility_schema_validation() -> None:
    payload = {
        "enhancedText": "Welcome to Nerdearla!",
        "soundDescriptions": ["[applause]"],
        "speakerTone": "energetic",
    }
    schema = AccessibilityEnhancementSchema(**payload)
    assert schema.enhancedText == "Welcome to Nerdearla!"
    assert schema.soundDescriptions == ["[applause]"]


@pytest.mark.asyncio
async def test_live_transcription_send_before_ready_fails() -> None:
    session = LiveTranscriptionSession()
    with pytest.raises(TranscriptionError, match="not ready to receive audio"):
        await session.send_audio_chunk(b"\x00\x00" * 160)


@pytest.mark.asyncio
async def test_live_translation_send_before_ready_fails() -> None:
    session = LiveTranslationSession()
    with pytest.raises(TranslationError, match="not ready to receive audio"):
        await session.send_audio_chunk(b"\x00\x00" * 160)


def test_get_genai_client_missing_project_raises_auth_error() -> None:
    from app.ai.client import get_genai_client, reset_genai_client
    from app.config import settings
    from app.errors import AuthError

    reset_genai_client()
    original = settings.google_cloud_project
    try:
        settings.google_cloud_project = ""
        with pytest.raises(AuthError, match="GOOGLE_CLOUD_PROJECT is required"):
            get_genai_client()
    finally:
        settings.google_cloud_project = original
        reset_genai_client()


def test_summary_function_annotation_inspection() -> None:
    import inspect
    from app.ai.summary import generate_executive_summary

    sig = inspect.signature(generate_executive_summary)
    assert "detected_chapters" in sig.parameters

