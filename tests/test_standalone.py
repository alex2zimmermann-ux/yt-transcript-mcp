"""Tests for standalone provider with mocked youtube-transcript-api."""

from unittest.mock import MagicMock, patch, AsyncMock
import pytest

from yt_transcript_mcp.providers.standalone import StandaloneProvider


class MockSnippet:
    def __init__(self, text, start, duration):
        self.text = text
        self.start = start
        self.duration = duration


@pytest.fixture
def mock_snippets():
    return [
        MockSnippet("Hello", 0.0, 2.0),
        MockSnippet("World", 2.0, 3.0),
    ]


class TestStandaloneProvider:
    @pytest.mark.asyncio
    async def test_get_transcript_success(self, mock_snippets):
        provider = StandaloneProvider()
        with patch.object(provider, "_fetch", return_value=mock_snippets):
            result = await provider.get_transcript("dQw4w9WgXcQ", "en")
        assert result.video_id == "dQw4w9WgXcQ"
        assert result.language == "en"
        assert result.method == "standalone"
        assert len(result.segments) == 2
        assert result.segments[0].text == "Hello"
        assert result.text == "Hello World"

    @pytest.mark.asyncio
    async def test_get_transcript_no_transcript(self):
        from youtube_transcript_api import TranscriptsDisabled
        provider = StandaloneProvider()
        with patch.object(
            provider, "_fetch", side_effect=TranscriptsDisabled("vid")
        ):
            with pytest.raises(ValueError, match="No transcript available"):
                await provider.get_transcript("vid123456789", "en")

    @pytest.mark.asyncio
    async def test_close(self):
        provider = StandaloneProvider()
        await provider.close()  # Should not raise
