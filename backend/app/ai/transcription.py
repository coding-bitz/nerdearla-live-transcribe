from __future__ import annotations
import asyncio
import time
from typing import AsyncGenerator, Dict, List, Optional
from google.genai import types
from app.ai.client import get_genai_client
from app.ai.models import TRANSCRIPTION_MODEL, assert_transcription_model
from app.errors import AIServiceError, TranscriptionError


class LiveTranscriptionSession:
    """Manages a live bidirectional streaming session with Gemini Transcribe."""

    def __init__(self, language_codes: Optional[List[str]] = None) -> None:
        assert_transcription_model(TRANSCRIPTION_MODEL)
        self.model = TRANSCRIPTION_MODEL
        self.language_codes = language_codes or ["es-ES", "en-US"]
        self._session_ctx = None
        self._session = None
        self._is_ready = asyncio.Event()
        self._is_closed = False

    async def start(self) -> None:
        """Establish Live API connection and wait for setup_complete before streaming."""
        config = types.LiveConnectConfig(
            response_modalities=["TEXT"],
            input_audio_transcription=types.AudioTranscriptionConfig(
                language_codes=self.language_codes,
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
            raise AIServiceError(f"Failed to connect to transcription service: {exc}") from exc

    async def wait_until_ready(self, timeout: float = 10.0) -> None:
        try:
            await asyncio.wait_for(self._is_ready.wait(), timeout=timeout)
        except asyncio.TimeoutError as exc:
            raise TranscriptionError("Timed out waiting for setup_complete from transcription service") from exc

    async def send_audio_chunk(self, pcm_bytes: bytes) -> None:
        """Stream raw 16kHz mono PCM chunk to the session."""
        if self._is_closed:
            raise TranscriptionError("Cannot send audio to a closed transcription session")
        if not self._is_ready.is_set():
            raise TranscriptionError("Transcription session is not ready to receive audio yet")

        try:
            await self._session.send_realtime_input(
                audio=types.Blob(
                    data=pcm_bytes,
                    mime_type="audio/pcm;rate=16000",
                )
            )
        except Exception as exc:
            raise TranscriptionError(f"Failed streaming audio chunk to transcription service: {exc}") from exc

    async def receive_events(self) -> AsyncGenerator[Dict[str, any], None]:
        """Receive and yield interim and final transcription results."""
        if self._session is None:
            raise TranscriptionError("Transcription session has not been started")

        try:
            async for response in self._session.receive():
                if self._is_closed:
                    break

                # The model must signal setup_complete before audio streaming can commence
                if response.setup_complete is not None:
                    self._is_ready.set()
                    yield {
                        "type": "ready",
                        "subtype": "transcription_ready",
                        "timestamp": int(time.time() * 1000),
                    }
                    continue

                server_content = response.server_content
                if server_content is None:
                    continue

                now_ms = int(time.time() * 1000)

                # Process interim transcription when available
                if server_content.interim_input_transcription is not None:
                    interim_text = server_content.interim_input_transcription.text
                    if interim_text and interim_text.strip():
                        yield {
                            "type": "transcription",
                            "subtype": "interim",
                            "text": interim_text.strip(),
                            "timestamp": now_ms,
                        }

                # Process input transcription
                if server_content.input_transcription is not None:
                    tx = server_content.input_transcription
                    if tx.text and tx.text.strip():
                        subtype = "final" if (tx.finished or server_content.turn_complete) else "interim"
                        yield {
                            "type": "transcription",
                            "subtype": subtype,
                            "text": tx.text.strip(),
                            "timestamp": now_ms,
                        }

                # Check turn complete with model parts if text was returned there
                if server_content.model_turn is not None and server_content.model_turn.parts:
                    for part in server_content.model_turn.parts:
                        if part.text and part.text.strip():
                            yield {
                                "type": "transcription",
                                "subtype": "final" if server_content.turn_complete else "interim",
                                "text": part.text.strip(),
                                "timestamp": now_ms,
                            }
        except Exception as exc:
            if not self._is_closed:
                raise TranscriptionError(f"Error receiving from transcription session: {exc}") from exc
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
