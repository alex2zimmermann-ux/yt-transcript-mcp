"""Standalone provider using youtube-transcript-api directly."""

import asyncio
import logging
from functools import partial

from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound

from yt_transcript_mcp.models import TranscriptResult, TranscriptSegment
from .base import TranscriptProvider

logger = logging.getLogger(__name__)


class StandaloneProvider(TranscriptProvider):
    def __init__(self):
        self._api = YouTubeTranscriptApi()

    async def get_transcript(
        self, video_id: str, language: str = "en"
    ) -> TranscriptResult:
        loop = asyncio.get_event_loop()
        try:
            fetched = await loop.run_in_executor(
                None,
                partial(self._fetch, video_id, language),
            )
        except (TranscriptsDisabled, NoTranscriptFound) as e:
            raise ValueError(f"No transcript available for {video_id}: {e}")

        segments = [
            TranscriptSegment(
                text=s.text,
                start=s.start,
                duration=s.duration,
            )
            for s in fetched
        ]
        full_text = " ".join(s.text for s in segments)
        detected_lang = language

        return TranscriptResult(
            video_id=video_id,
            language=detected_lang,
            is_generated=False,
            segments=segments,
            text=full_text,
            method="standalone",
        )

    def _fetch(self, video_id: str, language: str):
        """Synchronous fetch in executor."""
        return self._api.fetch(video_id, languages=[language, "en"])

    async def close(self) -> None:
        pass
