"""Live integration tests against Google Cloud GenAI models.

These tests execute real calls only when valid ADC credentials and
GOOGLE_CLOUD_PROJECT are configured in the environment.
If credentials or project are missing, tests are skipped with an explicit status:
'NOT EXECUTED — ADC credentials unavailable'.
"""

import os
import pytest
from app.ai.client import get_genai_client, reset_genai_client
from app.ai.models import TRANSCRIPTION_MODEL, TRANSLATION_MODEL, UTILITY_MODEL
from app.ai.transcription import LiveTranscriptionSession
from app.ai.translation import LiveTranslationSession
from app.config import settings

PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT") or settings.google_cloud_project
HAS_PROJECT = bool(PROJECT_ID and PROJECT_ID.strip())


def adc_credentials_available() -> bool:
    try:
        import google.auth
        _, project = google.auth.default()
        return True
    except Exception:
        # Check standard file location as well
        adc_path = os.path.expanduser("~/.config/gcloud/application_default_credentials.json")
        return os.path.exists(adc_path)


HAS_ADC = adc_credentials_available()


@pytest.mark.skipif(
    not (HAS_PROJECT and HAS_ADC),
    reason="NOT EXECUTED — ADC credentials unavailable or GOOGLE_CLOUD_PROJECT unset",
)
class TestRealGoogleCloudIntegration:
    @pytest.fixture(autouse=True)
    def setup_project(self):
        reset_genai_client()
        original = settings.google_cloud_project
        if not settings.google_cloud_project and PROJECT_ID:
            settings.google_cloud_project = PROJECT_ID
        yield
        settings.google_cloud_project = original
        reset_genai_client()

    @pytest.mark.asyncio
    async def test_real_flash_lite_model_invocation(self) -> None:
        client = get_genai_client()
        response = await client.aio.models.generate_content(
            model=UTILITY_MODEL,
            contents="Say 'Nerdearla Live Subtitles verification test successful' concisely.",
        )
        assert response.text is not None and len(response.text.strip()) > 0
        assert "Nerdearla" in response.text or len(response.text) > 5

    @pytest.mark.asyncio
    async def test_real_transcription_session_connection(self) -> None:
        session = LiveTranscriptionSession(language_codes=["es-ES"])
        try:
            await session.start()
            # Session successfully established live websocket to Gemini Live API
            assert session._session is not None
        finally:
            await session.close()

    @pytest.mark.asyncio
    async def test_real_translation_session_connection(self) -> None:
        session = LiveTranslationSession(target_language_code="es")
        try:
            await session.start()
            # Session successfully established live speech-to-speech websocket
            assert session._session is not None
        finally:
            await session.close()
