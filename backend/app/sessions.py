from __future__ import annotations
import json
import logging
import time
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from app.config import settings
from app.errors import SessionError
from app.redis import get_redis_client

logger = logging.getLogger(__name__)

SESSION_TTL_SECONDS = 86400  # 24 hours


class SessionState(BaseModel):
    session_id: str
    created_at: int = Field(default_factory=lambda: int(time.time() * 1000))
    status: str = "active"  # "active", "paused", "stopped"
    source_language: str = "es-ES"
    translation_enabled: bool = False
    target_language: str = "es"
    final_transcripts: List[Dict[str, Any]] = Field(default_factory=list)
    chapters: List[Dict[str, Any]] = Field(default_factory=list)
    summary: Optional[Dict[str, Any]] = None
    chunk_count: int = 0


class SessionManager:
    """Manages session persistence and shared state using Redis with in-memory local fallback."""

    def __init__(self) -> None:
        self._local_cache: Dict[str, SessionState] = {}

    def _redis_key(self, session_id: str) -> str:
        return f"nerdearla:session:{session_id}"

    async def get(self, session_id: str) -> Optional[SessionState]:
        try:
            redis = get_redis_client()
            raw_data = await redis.get(self._redis_key(session_id))
            if raw_data:
                state = SessionState.model_validate_json(raw_data)
                self._local_cache[session_id] = state
                return state
            return self._local_cache.get(session_id)
        except Exception as exc:
            if settings.environment == "production":
                raise SessionError(f"Redis unavailable in production environment: {exc}") from exc
            logger.warning(f"Redis get failed in development, using local fallback: {exc}")
            return self._local_cache.get(session_id)

    async def save(self, session: SessionState) -> None:
        self._local_cache[session.session_id] = session
        try:
            redis = get_redis_client()
            key = self._redis_key(session.session_id)
            await redis.set(key, session.model_dump_json(), ex=SESSION_TTL_SECONDS)
        except Exception as exc:
            if settings.environment == "production":
                raise SessionError(f"Redis unavailable in production environment: {exc}") from exc
            logger.warning(f"Redis save failed in development, stored in local cache only: {exc}")

    async def get_or_create(
        self,
        session_id: str,
        source_language: Optional[str] = None,
        translation_enabled: bool = False,
        target_language: Optional[str] = None,
    ) -> SessionState:
        existing = await self.get(session_id)
        if existing:
            return existing

        state = SessionState(
            session_id=session_id,
            source_language=source_language or settings.default_source_language,
            translation_enabled=translation_enabled,
            target_language=target_language or settings.default_translation_language,
        )
        await self.save(state)
        return state

    async def append_transcript(self, session_id: str, text: str, timestamp: int) -> None:
        session = await self.get(session_id)
        if not session:
            raise SessionError(f"Session '{session_id}' not found")

        session.final_transcripts.append({"text": text, "timestamp": timestamp})
        await self.save(session)

    async def add_chapter(self, session_id: str, chapter: Dict[str, Any]) -> None:
        session = await self.get(session_id)
        if not session:
            raise SessionError(f"Session '{session_id}' not found")

        session.chapters.append(chapter)
        await self.save(session)

    async def set_summary(self, session_id: str, summary: Dict[str, Any]) -> None:
        session = await self.get(session_id)
        if not session:
            raise SessionError(f"Session '{session_id}' not found")

        session.summary = summary
        await self.save(session)

    async def increment_chunk_count(self, session_id: str) -> int:
        session = await self.get(session_id)
        if not session:
            raise SessionError(f"Session '{session_id}' not found")

        session.chunk_count += 1
        await self.save(session)
        return session.chunk_count

    async def update_status(self, session_id: str, status: str) -> None:
        session = await self.get(session_id)
        if not session:
            raise SessionError(f"Session '{session_id}' not found")

        session.status = status
        await self.save(session)


session_manager = SessionManager()
