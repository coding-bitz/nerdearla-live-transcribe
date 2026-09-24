import pytest
from app.sessions import SessionManager, SessionState


@pytest.mark.asyncio
async def test_session_creation_and_retrieval() -> None:
    sm = SessionManager()
    session = await sm.get_or_create("test-sess-1", source_language="es-ES", translation_enabled=True)
    assert session.session_id == "test-sess-1"
    assert session.source_language == "es-ES"
    assert session.translation_enabled is True
    assert session.status == "active"

    retrieved = await sm.get("test-sess-1")
    assert retrieved is not None
    assert retrieved.session_id == "test-sess-1"


@pytest.mark.asyncio
async def test_session_append_transcript() -> None:
    sm = SessionManager()
    await sm.get_or_create("test-sess-2")
    await sm.append_transcript("test-sess-2", "Hello world", 1710000000000)

    session = await sm.get("test-sess-2")
    assert session is not None
    assert len(session.final_transcripts) == 1
    assert session.final_transcripts[0]["text"] == "Hello world"


@pytest.mark.asyncio
async def test_session_add_chapter_and_summary() -> None:
    sm = SessionManager()
    await sm.get_or_create("test-sess-3")
    await sm.add_chapter("test-sess-3", {"title": "Intro", "timestamp": 1710000000000})
    await sm.set_summary("test-sess-3", {"title": "Summary title", "summary": "Great talk"})

    session = await sm.get("test-sess-3")
    assert session is not None
    assert len(session.chapters) == 1
    assert session.chapters[0]["title"] == "Intro"
    assert session.summary["title"] == "Summary title"


@pytest.mark.asyncio
async def test_session_chunk_count_and_status() -> None:
    sm = SessionManager()
    await sm.get_or_create("test-sess-4")
    count = await sm.increment_chunk_count("test-sess-4")
    assert count == 1
    count = await sm.increment_chunk_count("test-sess-4")
    assert count == 2

    await sm.update_status("test-sess-4", "stopped")
    session = await sm.get("test-sess-4")
    assert session.status == "stopped"
