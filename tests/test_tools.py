"""Tests for MCP tool functions."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from yt_transcript_mcp.models import TranscriptResult, TranscriptSegment
from yt_transcript_mcp import server


@pytest.fixture(autouse=True)
def setup_server_state(sample_result):
    """Set up server module state for testing."""
    mock_provider = AsyncMock()
    mock_provider.get_transcript = AsyncMock(return_value=sample_result)

    server._provider = mock_provider
    server._cache = MagicMock()
    server._cache.get = MagicMock(return_value=None)
    server._cache.set = MagicMock()
    server._settings = MagicMock()
    server._settings.rate_limit_per_minute = 100
    server._rate_window.clear()
    yield
    server._rate_window.clear()


@pytest.fixture
def sample_segments():
    return [
        TranscriptSegment(text="Hello world", start=0.0, duration=2.5),
        TranscriptSegment(text="this is a test", start=2.5, duration=3.0),
        TranscriptSegment(text="of the transcript", start=5.5, duration=2.0),
        TranscriptSegment(text="extraction system", start=7.5, duration=2.5),
        TranscriptSegment(text="goodbye world", start=10.0, duration=2.0),
    ]


@pytest.fixture
def sample_result(sample_segments):
    return TranscriptResult(
        video_id="dQw4w9WgXcQ",
        language="en",
        is_generated=False,
        segments=sample_segments,
        text="Hello world this is a test of the transcript extraction system goodbye world",
        method="standalone",
    )


class TestGetTranscript:
    @pytest.mark.asyncio
    async def test_valid_url(self):
        result = await server.get_transcript("https://youtube.com/watch?v=dQw4w9WgXcQ")
        assert "## Transcript: dQw4w9WgXcQ" in result
        assert "Hello world" in result

    @pytest.mark.asyncio
    async def test_invalid_url(self):
        result = await server.get_transcript("not-a-url")
        assert "Error: Invalid YouTube URL" in result

    @pytest.mark.asyncio
    async def test_segments_format(self):
        result = await server.get_transcript("dQw4w9WgXcQ", format="segments")
        assert "**[0:00]**" in result


class TestSearchTranscript:
    @pytest.mark.asyncio
    async def test_found(self):
        result = await server.search_transcript("dQw4w9WgXcQ", "test")
        assert "1 match(es) found" in result

    @pytest.mark.asyncio
    async def test_not_found(self):
        result = await server.search_transcript("dQw4w9WgXcQ", "nonexistent")
        assert "No matches found" in result

    @pytest.mark.asyncio
    async def test_empty_query(self):
        result = await server.search_transcript("dQw4w9WgXcQ", "  ")
        assert "Error: Search query cannot be empty" in result


class TestGetTranscriptSummary:
    @pytest.mark.asyncio
    async def test_summary(self):
        result = await server.get_transcript_summary("dQw4w9WgXcQ", chunk_minutes=1)
        assert "## Transcript Summary: dQw4w9WgXcQ" in result
        assert "[0:00 - 1:00]" in result


class TestBatchTranscripts:
    @pytest.mark.asyncio
    async def test_batch(self):
        result = await server.batch_transcripts(["dQw4w9WgXcQ"])
        assert "## Batch Transcripts (1 videos)" in result

    @pytest.mark.asyncio
    async def test_batch_too_many(self):
        urls = [f"vid{i:09d}xx" for i in range(11)]
        result = await server.batch_transcripts(urls)
        assert "Maximum 10 videos" in result

    @pytest.mark.asyncio
    async def test_batch_invalid_url(self):
        result = await server.batch_transcripts(["not-valid"])
        assert "Invalid URL or video ID" in result


class TestRateLimit:
    @pytest.mark.asyncio
    async def test_rate_limit_exceeded(self):
        server._settings.rate_limit_per_minute = 2
        await server.get_transcript("dQw4w9WgXcQ")
        await server.get_transcript("dQw4w9WgXcQ")
        with pytest.raises(ValueError, match="Rate limit exceeded"):
            server._check_rate_limit()
