from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from app.ai.accessibility import enhance_for_accessibility
from app.ai.summary import generate_executive_summary
from app.config import ALLOWED_MODELS, settings
from app.redis import close_redis, ping_redis
from app.sessions import session_manager
from app.websocket import router as ws_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await close_redis()


app = FastAPI(
    title="Nerdearla Live Subtitles API",
    version="2.0.0",
    lifespan=lifespan,
)

# CORS configuration
allowed_origins = [settings.frontend_url]
if settings.environment == "development":
    allowed_origins.extend(["http://localhost:5173", "http://127.0.0.1:5173"])

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount WebSocket router
app.include_router(ws_router)


class AccessibilityRequest(BaseModel):
    text: str
    audio_features: Optional[Dict[str, float]] = None


@app.get("/health")
async def health_check() -> Dict[str, str]:
    return {"status": "ok"}


@app.get("/ready")
async def readiness_check() -> Dict[str, Any]:
    redis_healthy = await ping_redis()
    return {
        "status": "ready",
        "models": ALLOWED_MODELS,
        "redis_connected": redis_healthy,
        "environment": settings.environment,
    }


@app.get("/api/sessions/{session_id}")
async def get_session(session_id: str) -> Dict[str, Any]:
    session = await session_manager.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session.model_dump()


@app.post("/api/sessions/{session_id}/summary")
async def post_summary(session_id: str) -> Dict[str, Any]:
    session = await session_manager.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if not session.final_transcripts:
        raise HTTPException(status_code=400, detail="Cannot generate summary from empty transcript")

    transcript_lines = [t["text"] for t in session.final_transcripts]
    try:
        summary_result = await generate_executive_summary(
            full_transcript=transcript_lines,
            detected_chapters=session.chapters,
        )
        await session_manager.set_summary(session_id, summary_result)
        return summary_result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/api/sessions/{session_id}/accessibility")
async def post_accessibility(session_id: str, payload: AccessibilityRequest) -> Dict[str, Any]:
    try:
        result = await enhance_for_accessibility(
            text=payload.text,
            audio_features=payload.audio_features,
        )
        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
