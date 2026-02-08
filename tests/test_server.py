"""Tests for server startup."""

import pytest
from unittest.mock import patch, AsyncMock

from yt_transcript_mcp.server import mcp, app_lifespan
from yt_transcript_mcp.config import Mode, Settings


class TestServerStartup:
    @pytest.mark.asyncio
    async def test_standalone_lifespan(self):
        with patch("yt_transcript_mcp.server.Settings") as MockSettings:
            mock_settings = MockSettings.return_value
            mock_settings.mode = Mode.STANDALONE
            mock_settings.cache_max_size = 10
            mock_settings.cache_ttl_seconds = 60
            mock_settings.rate_limit_per_minute = 30

            async with app_lifespan(mcp):
                from yt_transcript_mcp import server
                assert server._provider is not None
                assert server._cache is not None

    @pytest.mark.asyncio
    async def test_backend_lifespan(self):
        with patch("yt_transcript_mcp.server.Settings") as MockSettings:
            mock_settings = MockSettings.return_value
            mock_settings.mode = Mode.BACKEND
            mock_settings.backend_url = "http://localhost:8300"
            mock_settings.backend_api_key = "test"
            mock_settings.cache_max_size = 10
            mock_settings.cache_ttl_seconds = 60
            mock_settings.rate_limit_per_minute = 30

            async with app_lifespan(mcp):
                from yt_transcript_mcp import server
                from yt_transcript_mcp.providers.backend import BackendProvider
                assert isinstance(server._provider, BackendProvider)
                await server._provider.close()

    def test_mcp_has_tools(self):
        # FastMCP should have our tools registered
        assert mcp is not None
        assert mcp.name == "YouTube Transcript"
