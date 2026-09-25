from __future__ import annotations
import json
import time
from typing import Any, Dict, List, Optional
from google.genai import types
from pydantic import BaseModel, Field
from app.ai.client import get_genai_client
from app.ai.models import UTILITY_MODEL, assert_utility_model
from app.errors import ChapterError


class ChapterDetectionSchema(BaseModel):
    chapterChange: bool = Field(description="True if a new technical topic or section began, False otherwise")
    title: str = Field(default="", description="Concise chapter title up to 5 words, in the speaker's language")


async def detect_chapter_change(
    recent_segments: List[str],
    current_topic: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Analyzes recent final transcript segments to detect topic shifts."""
    assert_utility_model(UTILITY_MODEL)

    if not recent_segments:
        return None

    transcript_block = "\n".join(recent_segments)
    current_topic_context = f"Current active topic: '{current_topic}'\n" if current_topic else "No chapter identified yet.\n"

    prompt = (
        f"{current_topic_context}"
        f"Recent talk segments:\n{transcript_block}\n\n"
        "Determine if a new major topic or chapter change occurred in the recent segments compared to the current topic. "
        "If yes, return chapterChange=true with a concise title (maximum 5 words). "
        "If no, return chapterChange=false with an empty title."
    )

    client = get_genai_client()
    try:
        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=ChapterDetectionSchema,
            temperature=0.2,
        )

        response = await client.aio.models.generate_content(
            model=UTILITY_MODEL,
            contents=prompt,
            config=config,
        )

        if not response.text:
            raise ChapterError("Empty response received from chapter detection model")

        data = json.loads(response.text)
        if data.get("chapterChange"):
            return {
                "chapterChange": True,
                "title": data.get("title", "").strip(),
                "timestamp": int(time.time() * 1000),
            }
        return None
    except Exception as exc:
        raise ChapterError(f"Chapter detection model invocation failed: {exc}") from exc
