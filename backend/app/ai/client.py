from typing import Optional
from google import genai
from app.config import settings
from app.errors import AuthError

_client: Optional[genai.Client] = None


def get_genai_client() -> genai.Client:
    global _client
    if _client is None:
        project_id = settings.google_cloud_project or "nerdearla-project"
        if not project_id:
            raise AuthError("GOOGLE_CLOUD_PROJECT must be configured to initialize Gemini client")
        _client = genai.Client(
            enterprise=True,
            project=project_id,
            location=settings.google_cloud_location,
        )
    return _client


# Default shared client instance
client = get_genai_client()
