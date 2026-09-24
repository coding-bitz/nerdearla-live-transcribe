import asyncio
import base64
import json
import logging
import time
from typing import Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.ai.accessibility import enhance_for_accessibility
from app.ai.chapters import detect_chapter_change
from app.ai.summary import generate_executive_summary
from app.ai.transcription import LiveTranscriptionSession
from app.ai.translation import LiveTranslationSession
from app.audio import compute_audio_metrics, validate_pcm16_chunk
from app.errors import (
    AppError,
    InvalidAudioFormatError,
    SessionError,
    WebSocketError,
    format_error_payload,
)
from app.sessions import session_manager

logger = logging.getLogger(__name__)

router = APIRouter()


class SessionConnectionHandler:
    """Coordinates real-time streaming between browser WebSocket and Gemini Live sessions."""

    def __init__(
        self,
        websocket: WebSocket,
        session_id: str,
        source_language: str = "es-ES",
        enable_translation: bool = False,
        target_language: str = "es",
    ) -> None:
        self.websocket = websocket
        self.session_id = session_id
        self.source_language = source_language
        self.enable_translation = enable_translation
        self.target_language = target_language

        self.tx_session: Optional[LiveTranscriptionSession] = None
        self.translate_session: Optional[LiveTranslationSession] = None

        self._tx_task: Optional[asyncio.Task] = None
        self._translate_task: Optional[asyncio.Task] = None
        self._chapter_task: Optional[asyncio.Task] = None

        self._running = False
        self._last_chapter_check = time.time()
        self._current_chapter_title: Optional[str] = None
        self._recent_final_segments: list[str] = []
        self._latest_audio_metrics: dict[str, float] = {"volume_rms": 0.0}

    async def send_json(self, data: dict) -> None:
        try:
            await self.websocket.send_text(json.dumps(data))
        except Exception:
            pass

    async def initialize(self) -> None:
        await session_manager.get_or_create(
            self.session_id,
            source_language=self.source_language,
            translation_enabled=self.enable_translation,
            target_language=self.target_language,
        )

        self._running = True

        # Initialize live transcription session
        self.tx_session = LiveTranscriptionSession(language_codes=[self.source_language])
        try:
            await self.tx_session.start()
        except Exception as exc:
            await self.send_json(format_error_payload("AI_SERVICE_ERROR", f"Transcription service failed to connect: {exc}"))
            raise

        self._tx_task = asyncio.create_task(self._listen_transcription())

        # Initialize live translation session only if translation requested
        if self.enable_translation:
            await self._start_translation_service(self.target_language)

        # Chapter detection background loop
        self._chapter_task = asyncio.create_task(self._chapter_detection_loop())

    async def _start_translation_service(self, target_lang: str) -> None:
        self.translate_session = LiveTranslationSession(target_language_code=target_lang)
        try:
            await self.translate_session.start()
            self._translate_task = asyncio.create_task(self._listen_translation())
        except Exception as exc:
            await self.send_json(format_error_payload("AI_SERVICE_ERROR", f"Translation service failed to connect: {exc}"))
            self.translate_session = None

    async def _listen_transcription(self) -> None:
        if not self.tx_session:
            return
        try:
            async for event in self.tx_session.receive_events():
                if not self._running:
                    break

                if event.get("type") == "ready":
                    # Emit ready status to client
                    await self.send_json({
                        "type": "ready",
                        "sessionId": self.session_id,
                    })
                    continue

                if event.get("type") == "transcription":
                    await self.send_json(event)

                    if event.get("subtype") == "final":
                        text = event.get("text", "")
                        timestamp = event.get("timestamp", int(time.time() * 1000))
                        await session_manager.append_transcript(self.session_id, text, timestamp)
                        self._recent_final_segments.append(text)
        except Exception as exc:
            logger.error(f"Error in transcription loop: {exc}")
            await self.send_json(format_error_payload("TRANSCRIPTION_ERROR", str(exc)))

    async def _listen_translation(self) -> None:
        if not self.translate_session:
            return
        try:
            async for event in self.translate_session.receive_events():
                if not self._running:
                    break

                if event.get("type") == "translation":
                    await self.send_json(event)
        except Exception as exc:
            logger.error(f"Error in translation loop: {exc}")
            await self.send_json(format_error_payload("TRANSLATION_ERROR", str(exc)))

    async def _chapter_detection_loop(self) -> None:
        while self._running:
            await asyncio.sleep(30.0)
            if not self._running or len(self._recent_final_segments) < 3:
                continue

            now = time.time()
            if now - self._last_chapter_check >= 30.0:
                self._last_chapter_check = now
                segments_to_analyze = list(self._recent_final_segments[-8:])
                try:
                    result = await detect_chapter_change(
                        recent_segments=segments_to_analyze,
                        current_topic=self._current_chapter_title,
                    )
                    if result and result.get("chapterChange"):
                        new_title = result.get("title", "")
                        self._current_chapter_title = new_title
                        chapter_payload = {
                            "title": new_title,
                            "timestamp": result.get("timestamp", int(time.time() * 1000)),
                        }
                        await session_manager.add_chapter(self.session_id, chapter_payload)
                        await self.send_json({
                            "type": "chapter",
                            "chapter": chapter_payload,
                        })
                except Exception as exc:
                    logger.error(f"Chapter detection error: {exc}")
                    await self.send_json(format_error_payload("CHAPTER_ERROR", str(exc)))

    async def handle_audio_bytes(self, pcm_bytes: bytes) -> None:
        try:
            validate_pcm16_chunk(pcm_bytes)
        except InvalidAudioFormatError as err:
            await self.send_json(err.to_dict())
            return

        self._latest_audio_metrics = compute_audio_metrics(pcm_bytes)
        await session_manager.increment_chunk_count(self.session_id)

        # Send to transcription
        if self.tx_session:
            try:
                await self.tx_session.send_audio_chunk(pcm_bytes)
            except Exception as exc:
                await self.send_json(format_error_payload("TRANSCRIPTION_ERROR", str(exc)))

        # Send to translation if active
        if self.translate_session:
            try:
                await self.translate_session.send_audio_chunk(pcm_bytes)
            except Exception as exc:
                await self.send_json(format_error_payload("TRANSLATION_ERROR", str(exc)))

    async def handle_client_message(self, message: str) -> None:
        try:
            data = json.loads(message)
        except json.JSONDecodeError:
            await self.send_json(format_error_payload("WEBSOCKET_ERROR", "Invalid JSON payload"))
            return

        msg_type = data.get("type")

        if msg_type == "audio":
            b64_data = data.get("data", "")
            try:
                pcm_bytes = base64.b64decode(b64_data)
                await self.handle_audio_bytes(pcm_bytes)
            except Exception as exc:
                await self.send_json(format_error_payload("INVALID_AUDIO_FORMAT", f"Base64 audio decode failed: {exc}"))

        elif msg_type == "stop":
            await session_manager.update_status(self.session_id, "stopped")
            await self.cleanup()

        elif msg_type == "start_translation":
            target_lang = data.get("target_language", self.target_language)
            self.enable_translation = True
            self.target_language = target_lang
            if self.translate_session is None:
                await self._start_translation_service(target_lang)

        elif msg_type == "stop_translation":
            self.enable_translation = False
            if self.translate_session is not None:
                await self.translate_session.close()
                self.translate_session = None

        elif msg_type == "request_summary":
            await self.trigger_summary()

        elif msg_type == "request_accessibility":
            text = data.get("text", "")
            await self.trigger_accessibility(text)

    async def trigger_summary(self) -> None:
        session = await session_manager.get(self.session_id)
        if not session or not session.final_transcripts:
            await self.send_json(format_error_payload("SUMMARY_ERROR", "Cannot generate summary with empty transcripts"))
            return

        transcript_lines = [t["text"] for t in session.final_transcripts]
        try:
            summary_data = await generate_executive_summary(
                full_transcript=transcript_lines,
                detected_chapters=session.chapters,
            )
            await session_manager.set_summary(self.session_id, summary_data)
            await self.send_json({
                "type": "summary",
                "summary": summary_data,
            })
        except Exception as exc:
            await self.send_json(format_error_payload("SUMMARY_ERROR", str(exc)))

    async def trigger_accessibility(self, text: str) -> None:
        try:
            result = await enhance_for_accessibility(
                text=text,
                audio_features=self._latest_audio_metrics,
            )
            await self.send_json({
                "type": "accessibility",
                "accessibility": result,
            })
        except Exception as exc:
            await self.send_json(format_error_payload("ACCESSIBILITY_ERROR", str(exc)))

    async def cleanup(self) -> None:
        self._running = False

        for task in [self._tx_task, self._translate_task, self._chapter_task]:
            if task and not task.done():
                task.cancel()

        if self.tx_session:
            await self.tx_session.close()
            self.tx_session = None

        if self.translate_session:
            await self.translate_session.close()
            self.translate_session = None


@router.websocket("/ws/{session_id}")
async def websocket_session_endpoint(
    websocket: WebSocket,
    session_id: str,
    source_language: str = "es-ES",
    translate: bool = False,
    target_language: str = "es",
) -> None:
    await websocket.accept()

    handler = SessionConnectionHandler(
        websocket=websocket,
        session_id=session_id,
        source_language=source_language,
        enable_translation=translate,
        target_language=target_language,
    )

    try:
        await handler.initialize()
    except Exception as exc:
        logger.error(f"Failed to initialize session handler: {exc}")
        await handler.cleanup()
        return

    try:
        while True:
            message = await websocket.receive()
            if "bytes" in message and message["bytes"]:
                await handler.handle_audio_bytes(message["bytes"])
            elif "text" in message and message["text"]:
                await handler.handle_client_message(message["text"])
    except WebSocketDisconnect:
        logger.info(f"WebSocket client disconnected for session {session_id}")
    except Exception as exc:
        logger.error(f"WebSocket session error: {exc}")
    finally:
        await handler.cleanup()
