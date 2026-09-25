from __future__ import annotations
import asyncio
import time
from typing import AsyncGenerator, Dict, Optional
from google.genai import types
from app.ai.client import get_genai_client
from app.ai.models import TRANSLATION_MODEL, assert_translation_model
from app.errors import AIServiceError, TranslationError


class LiveTranslationSession:
    """Manages a live speech-to-speech translation session extracting text subtitles."""

    def __init__(self, target_language_code: str = "es") -> None:
        assert_translation_model(TRANSLATION_MODEL)
        self.model = TRANSLATION_MODEL
        self.target_language_code = target_language_code
        self._session_ctx = None
        self._session = None
        self._is_ready = asyncio.Event()
        self._is_closed = False

    async def start(self) -> None:
        # Live translation operates in speech-to-speech mode; output text is extracted from output_audio_transcription
        config = types.LiveConnectConfig(
            response_modalities=["AUDIO"],
            input_audio_transcription=types.AudioTranscriptionConfig(),
            output_audio_transcription=types.AudioTranscriptionConfig(),
            translation_config=types.TranslationConfig(
                target_language_code=self.target_language_code,
                echo_target_language=True,
            ),
        )

        client = get_genai_client()
        try:
            self._session_ctx = client.aio.live.connect(
                model=self.model,
                config=config,
            )
            self._session = await self._session_ctx.__aenter__()
        except Exception as exc:
            raise AIServiceError(f"Failed to connect to translation service: {exc}") from exc

    async def wait_until_ready(self, timeout: float = 10.0) -> None:
        try:
            await asyncio.wait_for(self._is_ready.wait(), timeout=timeout)
        except asyncio.TimeoutError as exc:
            raise TranslationError("Timed out waiting for setup_complete from translation service") from exc

    async def send_audio_chunk(self, pcm_bytes: bytes) -> None:
        """Stream raw 16kHz mono PCM chunk to translation session."""
        if self._is_closed:
            raise TranslationError("Cannot send audio to a closed translation session")
        if not self._is_ready.is_set():
            raise TranslationError("Translation session is not ready to receive audio yet")

        try:
            await self._session.send_realtime_input(
                audio=types.Blob(
                    data=pcm_bytes,
                    mime_type="audio/pcm;rate=16000",
                )
            )
        except Exception as exc:
            raise TranslationError(f"Failed streaming audio chunk to translation service: {exc}") from exc

    async def receive_events(self) -> AsyncGenerator[Dict[str, any], None]:
        """Receive and yield translated subtitle text extracted from model output."""
        if self._session is None:
            raise TranslationError("Translation session has not been started")

        try:
            async for response in self._session.receive():
                if self._is_closed:
                    break

                if response.setup_complete is not None:
                    self._is_ready.set()
                    yield {
                        "type": "ready",
                        "subtype": "translation_ready",
                        "timestamp": int(time.time() * 1000),
                    }
                    continue

                server_content = response.server_content
                if server_content is None:
                    continue

                now_ms = int(time.time() * 1000)

                # Translation text comes strictly from output_transcription
                if server_content.output_transcription is not None:
                    text = server_content.output_transcription.text
                    if text and text.strip():
                        yield {
                            "type": "translation",
                            "subtype": "translation",
                            "text": text.strip(),
                            "timestamp": now_ms,
                        }
        except Exception as exc:
            if not self._is_closed:
                raise TranslationError(f"Error receiving from translation session: {exc}") from exc
        finally:
            await self.close()

    async def close(self) -> None:
        if self._is_closed:
            return
        self._is_closed = True
        if self._session_ctx is not None:
            try:
                await self._session_ctx.__aexit__(None, None, None)
            except Exception:
                pass
            self._session_ctx = None
            self._session = None
