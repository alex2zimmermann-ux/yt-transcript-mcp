"""Tests for backend provider with httpx mocking."""

import pytest
import httpx
import respx

from yt_transcript_mcp.providers.backend import BackendProvider


@pytest.fixture
def backend():
    return BackendProvider(base_url="http://test-backend:8300", api_key="test-key")


class TestBackendProvider:
    @respx.mock
    @pytest.mark.asyncio
    async def test_get_transcript_success(self, backend):
        respx.get("http://test-backend:8300/transcript/dQw4w9WgXcQ").mock(
            return_value=httpx.Response(200, json={
                "video_id": "dQw4w9WgXcQ",
                "method": "cookie_transcript",
                "language": "en",
                "text": "Hello world",
                "segments": [
                    {"text": "Hello", "start": 0.0, "duration": 2.0},
                    {"text": "world", "start": 2.0, "duration": 2.0},
                ],
                "metadata": {"is_generated": False, "processing_time": 0.5, "cached": False},
            })
        )
        result = await backend.get_transcript("dQw4w9WgXcQ", "en")
        assert result.video_id == "dQw4w9WgXcQ"
        assert result.language == "en"
        assert len(result.segments) == 2
        assert result.text == "Hello world"
        await backend.close()

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_transcript_timeout(self, backend):
        respx.get("http://test-backend:8300/transcript/dQw4w9WgXcQ").mock(
            side_effect=httpx.ReadTimeout("Timeout")
        )
        with pytest.raises(httpx.ReadTimeout):
            await backend.get_transcript("dQw4w9WgXcQ", "en")
        await backend.close()

    @respx.mock
    @pytest.mark.asyncio
    async def test_batch_success(self, backend):
        respx.post("http://test-backend:8300/transcript").mock(
            return_value=httpx.Response(200, json={
                "results": [
                    {
                        "video_id": "vid1_______",
                        "method": "ytdlp",
                        "language": "en",
                        "text": "First video",
                        "segments": [{"text": "First video", "start": 0.0, "duration": 3.0}],
                        "metadata": {"is_generated": False},
                    },
                    {"video_id": "vid2_______", "error": "Not found"},
                ]
            })
        )
        results = await backend.get_batch(["vid1_______", "vid2_______"], "en")
        assert len(results) == 2
        assert results[0].video_id == "vid1_______"
        assert isinstance(results[1], dict)
        assert "error" in results[1]
        await backend.close()
