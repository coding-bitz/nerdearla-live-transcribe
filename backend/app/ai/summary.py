import json
from typing import Any, Dict, List, Literal
from google.genai import types
from pydantic import BaseModel, Field
from app.ai.client import get_genai_client
from app.ai.models import UTILITY_MODEL, assert_utility_model
from app.errors import SummaryError


class ChapterSummaryItem(BaseModel):
    title: str = Field(description="Title of the chapter")
    summary: str = Field(description="Brief 1-2 sentence description of chapter contents")


class ExecutiveSummarySchema(BaseModel):
    title: str = Field(description="Comprehensive presentation title derived from talk content")
    summary: str = Field(description="Executive summary of the entire talk (2-3 paragraphs)")
    keyTakeaways: List[str] = Field(description="Key technical takeaways and action items")
    resources: List[str] = Field(default_factory=list, description="Verified tools, libraries, or links explicitly mentioned in talk. Leave empty if none mentioned.")
    technicalLevel: Literal["beginner", "intermediate", "advanced"] = Field(description="Assessed technical depth")
    topics: List[str] = Field(description="Main technical topics covered")
    hashtags: List[str] = Field(description="Relevant social hashtags e.g. #Python #Cloud")
    estimatedReadingTime: str = Field(description="Estimated reading time e.g. '3 min'")
    chapters: List[ChapterSummaryItem] = Field(default_factory=list, description="Structured chapters overview")


async def generate_executive_summary(
    full_transcript: List[str],
    detected_chapters: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Generates a structured post-session executive summary from real transcript."""
    assert_utility_model(UTILITY_MODEL)

    if not full_transcript:
        raise SummaryError("Cannot generate summary from an empty transcript")

    transcript_text = "\n".join(full_transcript)
    chapters_context = ""
    if detected_chapters:
        chapters_lines = [f"- {c.get('title', 'Untitled')} at {c.get('timestamp', '')}" for c in detected_chapters]
        chapters_context = "Detected session chapters:\n" + "\n".join(chapters_lines) + "\n\n"

    prompt = (
        "Generate a structured executive technical summary based strictly on the talk transcript provided.\n"
        "Important: Do not invent external resources or fake URLs. If no explicit tools, libraries, or links were mentioned, leave resources empty.\n\n"
        f"{chapters_context}"
        f"Transcript:\n{transcript_text}"
    )

    client = get_genai_client()
    try:
        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=ExecutiveSummarySchema,
            temperature=0.3,
        )

        response = await client.aio.models.generate_content(
            model=UTILITY_MODEL,
            contents=prompt,
            config=config,
        )

        if not response.text:
            raise SummaryError("Empty response received from summary model")

        return json.loads(response.text)
    except Exception as exc:
        raise SummaryError(f"Executive summary generation failed: {exc}") from exc
