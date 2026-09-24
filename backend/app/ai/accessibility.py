import json
from typing import Any, Dict, List, Optional
from google.genai import types
from pydantic import BaseModel, Field
from app.ai.client import get_genai_client
from app.ai.models import UTILITY_MODEL, assert_utility_model
from app.errors import AccessibilityError


class AccessibilityEnhancementSchema(BaseModel):
    enhancedText: str = Field(description="Clear, accessible subtitle text with standard punctuation and capitalization")
    soundDescriptions: List[str] = Field(default_factory=list, description="Descriptive non-speech audio cues only if clearly indicated, e.g. [applause], [laughter]")
    speakerTone: str = Field(default="", description="Tone or delivery pacing based on actual speaker cues")


async def enhance_for_accessibility(
    text: str,
    audio_features: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    """Enhances subtitles with accessibility formatting and descriptive sound cues."""
    assert_utility_model(UTILITY_MODEL)

    if not text or not text.strip():
        raise AccessibilityError("Cannot enhance empty subtitle text")

    features_context = ""
    if audio_features:
        features_context = f"Observed audio signals: {json.dumps(audio_features)}\n"

    prompt = (
        "Enhance the following live subtitle segment for hard-of-hearing and accessibility display.\n"
        "Ensure clear punctuation and technical formatting. Only add sound descriptions if evidenced by the input text or observed audio signals.\n"
        "Do not invent fake background sounds or simulated metrics.\n\n"
        f"{features_context}"
        f"Input subtitle:\n\"{text.strip()}\""
    )

    client = get_genai_client()
    try:
        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=AccessibilityEnhancementSchema,
            temperature=0.1,
        )

        response = await client.aio.models.generate_content(
            model=UTILITY_MODEL,
            contents=prompt,
            config=config,
        )

        if not response.text:
            raise AccessibilityError("Empty response received from accessibility model")

        return json.loads(response.text)
    except Exception as exc:
        raise AccessibilityError(f"Accessibility enhancement failed: {exc}") from exc
