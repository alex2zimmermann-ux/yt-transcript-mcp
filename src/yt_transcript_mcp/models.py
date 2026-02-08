"""Data models for transcript results."""

from pydantic import BaseModel


class TranscriptSegment(BaseModel):
    text: str
    start: float
    duration: float


class TranscriptResult(BaseModel):
    video_id: str
    language: str
    is_generated: bool = False
    segments: list[TranscriptSegment] = []
    text: str = ""
    method: str = "unknown"


class SearchMatch(BaseModel):
    text: str
    start: float
    duration: float
    segment_index: int
