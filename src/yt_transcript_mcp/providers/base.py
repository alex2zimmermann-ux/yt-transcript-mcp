"""Abstract base for transcript providers."""

from abc import ABC, abstractmethod

from yt_transcript_mcp.models import TranscriptResult


class TranscriptProvider(ABC):
    @abstractmethod
    async def get_transcript(
        self, video_id: str, language: str = "en"
    ) -> TranscriptResult:
        """Fetch transcript for a single video."""
        ...

    async def get_batch(
        self, video_ids: list[str], language: str = "en"
    ) -> list[TranscriptResult | dict]:
        """Fetch transcripts for multiple videos. Default: sequential."""
        results = []
        for vid in video_ids:
            try:
                results.append(await self.get_transcript(vid, language))
            except Exception as e:
                results.append({"video_id": vid, "error": str(e)})
        return results

    @abstractmethod
    async def close(self) -> None:
        """Clean up resources."""
        ...
