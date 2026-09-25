from __future__ import annotations
from typing import Optional
from google import genai
from app.config import settings
from app.errors import AuthError

_client: Optional[genai.Client] = None


def get_genai_client() -> genai.Client:
    """Returns the shared Google GenAI client instance authenticated via ADC."""
    global _client
    if _client is None:
        project_id = settings.google_cloud_project
        if not project_id or not project_id.strip():
            raise AuthError("GOOGLE_CLOUD_PROJECT is required to initialize Gemini client")

        _client = genai.Client(
            enterprise=True,
            project=project_id.strip(),
            location=settings.google_cloud_location,
        )
    return _client


def reset_genai_client() -> None:
    """Resets the cached client instance (useful for tests or configuration changes)."""
    global _client
    _client = None
