"""Shared test fixtures."""

import pytest

from yt_transcript_mcp.models import TranscriptResult, TranscriptSegment


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
