"""YouTube Transcript MCP Server."""

import logging
import sys
import time
from collections import deque
from contextlib import asynccontextmanager

from mcp.server.fastmcp import FastMCP

from yt_transcript_mcp.cache import TranscriptCache
from yt_transcript_mcp.config import Mode, Settings, Transport
from yt_transcript_mcp.models import TranscriptResult, TranscriptSegment
from yt_transcript_mcp.providers.backend import BackendProvider
from yt_transcript_mcp.providers.standalone import StandaloneProvider
from yt_transcript_mcp.utils import extract_video_id, format_timestamp

# Logging to stderr (MCP convention)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("yt-transcript-mcp")

# Module-level state
_provider = None
_cache = None
_settings = None
_rate_window = deque()


@asynccontextmanager
async def app_lifespan(server: FastMCP):
    global _provider, _cache, _settings, _rate_window
    _settings = Settings()
    _cache = TranscriptCache(
        max_size=_settings.cache_max_size,
        ttl=_settings.cache_ttl_seconds,
    )
    _rate_window = deque()

    if _settings.mode == Mode.BACKEND:
        _provider = BackendProvider(
            base_url=_settings.backend_url,
            api_key=_settings.backend_api_key,
        )
        logger.info(f"Backend mode: {_settings.backend_url}")
    else:
        _provider = StandaloneProvider()
        logger.info("Standalone mode")

    logger.info("Server started")
    yield

    if _provider:
        await _provider.close()
    logger.info("Server stopped")


mcp = FastMCP(
    "YouTube Transcript",
    instructions="Extract and search YouTube video transcripts",
    lifespan=app_lifespan,
)


def _check_rate_limit():
    """Sliding window rate limit."""
    now = time.time()
    limit = (_settings.rate_limit_per_minute if _settings else 30)
    while _rate_window and _rate_window[0] < now - 60:
        _rate_window.popleft()
    if len(_rate_window) >= limit:
        raise ValueError(
            f"Rate limit exceeded ({limit}/min). Try again in a few seconds."
        )
    _rate_window.append(now)


async def _get_transcript_cached(
    video_id: str, language: str
) -> TranscriptResult:
    """Get transcript with cache layer."""
    cached = _cache.get(video_id, language)
    if cached:
        return TranscriptResult(**cached)

    result = await _provider.get_transcript(video_id, language)
    _cache.set(video_id, language, result.model_dump())
    return result


def _segments_to_markdown(segments: list[TranscriptSegment]) -> str:
    """Format segments as markdown with timestamps."""
    lines = []
    for seg in segments:
        ts = format_timestamp(seg.start)
        lines.append(f"**[{ts}]** {seg.text}")
    return "\n".join(lines)


@mcp.tool()
async def get_transcript(
    url: str,
    language: str = "en",
    format: str = "text",
) -> str:
    """Get the transcript of a YouTube video.

    Args:
        url: YouTube video URL or video ID
        language: Language code (e.g. 'en', 'de', 'es'). Default: 'en'
        format: Output format - 'text' (plain text), 'segments' (timestamped), or 'both'. Default: 'text'
    """
    _check_rate_limit()

    video_id = extract_video_id(url)
    if not video_id:
        return f"Error: Invalid YouTube URL or video ID: {url}"

    try:
        result = await _get_transcript_cached(video_id, language)
    except Exception as e:
        return f"Error fetching transcript for {video_id}: {e}"

    header = f"## Transcript: {video_id}\n**Language:** {result.language} | **Method:** {result.method}\n"

    if format == "segments":
        body = _segments_to_markdown(result.segments)
    elif format == "both":
        body = (
            f"### Full Text\n{result.text}\n\n"
            f"### Timestamped Segments\n{_segments_to_markdown(result.segments)}"
        )
    else:
        body = result.text

    return f"{header}\n{body}"


@mcp.tool()
async def search_transcript(
    url: str,
    query: str,
    language: str = "en",
    context_segments: int = 1,
) -> str:
    """Search for keywords in a YouTube video transcript.

    Args:
        url: YouTube video URL or video ID
        query: Search query (case-insensitive)
        language: Language code. Default: 'en'
        context_segments: Number of surrounding segments to include. Default: 1
    """
    _check_rate_limit()

    video_id = extract_video_id(url)
    if not video_id:
        return f"Error: Invalid YouTube URL or video ID: {url}"

    if not query.strip():
        return "Error: Search query cannot be empty."

    try:
        result = await _get_transcript_cached(video_id, language)
    except Exception as e:
        return f"Error fetching transcript for {video_id}: {e}"

    query_lower = query.lower()
    matches = []
    segments = result.segments

    for i, seg in enumerate(segments):
        if query_lower in seg.text.lower():
            start_idx = max(0, i - context_segments)
            end_idx = min(len(segments), i + context_segments + 1)
            context = segments[start_idx:end_idx]
            match_text = "\n".join(
                f"{'> ' if j == i else '  '}"
                f"**[{format_timestamp(s.start)}]** {s.text}"
                for j, s in zip(range(start_idx, end_idx), context)
            )
            matches.append(match_text)

    if not matches:
        return f"No matches found for '{query}' in {video_id}."

    header = (
        f"## Search Results: '{query}' in {video_id}\n"
        f"**{len(matches)} match(es) found**\n"
    )
    body = "\n\n---\n\n".join(matches)
    return f"{header}\n{body}"


@mcp.tool()
async def get_transcript_summary(
    url: str,
    language: str = "en",
    chunk_minutes: int = 5,
) -> str:
    """Get a transcript structured in time chunks for easier analysis.

    Args:
        url: YouTube video URL or video ID
        language: Language code. Default: 'en'
        chunk_minutes: Size of each time chunk in minutes. Default: 5
    """
    _check_rate_limit()

    video_id = extract_video_id(url)
    if not video_id:
        return f"Error: Invalid YouTube URL or video ID: {url}"

    try:
        result = await _get_transcript_cached(video_id, language)
    except Exception as e:
        return f"Error fetching transcript for {video_id}: {e}"

    chunk_seconds = chunk_minutes * 60
    chunks: dict[int, list[TranscriptSegment]] = {}

    for seg in result.segments:
        chunk_idx = int(seg.start // chunk_seconds)
        chunks.setdefault(chunk_idx, []).append(seg)

    header = (
        f"## Transcript Summary: {video_id}\n"
        f"**Language:** {result.language} | **Chunk size:** {chunk_minutes}min\n"
    )
    parts = []
    for idx in sorted(chunks.keys()):
        start_ts = format_timestamp(idx * chunk_seconds)
        end_ts = format_timestamp((idx + 1) * chunk_seconds)
        text = " ".join(s.text for s in chunks[idx])
        parts.append(f"### [{start_ts} - {end_ts}]\n{text}")

    return f"{header}\n" + "\n\n".join(parts)


@mcp.tool()
async def batch_transcripts(
    urls: list[str],
    language: str = "en",
) -> str:
    """Get transcripts for multiple YouTube videos at once (max 10).

    Args:
        urls: List of YouTube video URLs or IDs (max 10)
        language: Language code. Default: 'en'
    """
    _check_rate_limit()

    if len(urls) > 10:
        return "Error: Maximum 10 videos per batch."

    video_ids = []
    for u in urls:
        vid = extract_video_id(u)
        video_ids.append(vid)

    results = []
    for raw_url, vid in zip(urls, video_ids):
        if vid is None:
            results.append(f"### {raw_url}\n**Error:** Invalid URL or video ID\n")
            continue
        try:
            result = await _get_transcript_cached(vid, language)
            text_preview = result.text[:500]
            if len(result.text) > 500:
                text_preview += "..."
            results.append(
                f"### {vid}\n**Language:** {result.language} | "
                f"**Segments:** {len(result.segments)}\n\n{text_preview}\n"
            )
        except Exception as e:
            results.append(f"### {vid}\n**Error:** {e}\n")

    header = f"## Batch Transcripts ({len(urls)} videos)\n"
    return header + "\n---\n\n".join(results)


def main():
    settings = Settings()
    if settings.transport == Transport.STREAMABLE_HTTP:
        mcp.run(transport="streamable-http")
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
