"""Backend provider that calls the existing VPS transcript service."""

import logging

import httpx

from yt_transcript_mcp.models import TranscriptResult, TranscriptSegment
from .base import TranscriptProvider

logger = logging.getLogger(__name__)


class BackendProvider(TranscriptProvider):
    def __init__(self, base_url: str, api_key: str = ""):
        self._base_url = base_url.rstrip("/")
        self._headers = {}
        if api_key:
            self._headers["X-API-Key"] = api_key
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            headers=self._headers,
            timeout=60.0,
        )

    async def get_transcript(
        self, video_id: str, language: str = "en"
    ) -> TranscriptResult:
        resp = await self._client.get(
            f"/transcript/{video_id}",
            params={"lang": language, "format": "both"},
        )
        resp.raise_for_status()
        data = resp.json()

        segments = [
            TranscriptSegment(
                text=s["text"],
                start=s["start"],
                duration=s["duration"],
            )
            for s in data.get("segments", [])
        ]

        return TranscriptResult(
            video_id=data["video_id"],
            language=data.get("language", language),
            is_generated=data.get("metadata", {}).get("is_generated", False),
            segments=segments,
            text=data.get("text", ""),
            method=data.get("method", "backend"),
        )

    async def get_batch(
        self, video_ids: list[str], language: str = "en"
    ) -> list[TranscriptResult | dict]:
        resp = await self._client.post(
            "/transcript",
            json={"video_ids": video_ids, "lang": language, "format": "both"},
        )
        resp.raise_for_status()
        data = resp.json()

        results = []
        for item in data.get("results", []):
            if "error" in item:
                results.append(item)
                continue
            segments = [
                TranscriptSegment(
                    text=s["text"], start=s["start"], duration=s["duration"]
                )
                for s in item.get("segments", [])
            ]
            results.append(
                TranscriptResult(
                    video_id=item["video_id"],
                    language=item.get("language", language),
                    is_generated=item.get("metadata", {}).get("is_generated", False),
                    segments=segments,
                    text=item.get("text", ""),
                    method=item.get("method", "backend"),
                )
            )
        return results

    async def close(self) -> None:
        await self._client.aclose()
