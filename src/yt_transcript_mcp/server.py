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



# ── MCP Prompts (Smithery quality) ──────────────────────────────────────────


@mcp.prompt()
def summarize_video(url: str) -> str:
    """Generate a comprehensive summary of a YouTube video from its transcript.

    Args:
        url: YouTube video URL or video ID to summarize
    """
    return f"""Please use the get_transcript tool to fetch the transcript for this YouTube video: {url}

Then provide a comprehensive summary including:
1. Main topic and key points
2. Important quotes or statements
3. A brief conclusion

Keep the summary concise but informative."""


@mcp.prompt()
def compare_videos(url1: str, url2: str) -> str:
    """Compare the content of two YouTube videos side by side.

    Args:
        url1: First YouTube video URL or ID
        url2: Second YouTube video URL or ID
    """
    return f"""Please use the batch_transcripts tool to fetch transcripts for these two videos:
- Video 1: {url1}
- Video 2: {url2}

Then compare them:
1. What topics does each video cover?
2. Where do they agree or disagree?
3. Which provides more depth on the subject?
4. Key differences in perspective or approach"""


@mcp.prompt()
def find_key_moments(url: str, topic: str) -> str:
    """Find and analyze key moments in a video related to a specific topic.

    Args:
        url: YouTube video URL or video ID
        topic: The topic or keyword to search for
    """
    return f"""Please use the search_transcript tool to find mentions of "{topic}" in this video: {url}

Then use get_transcript_summary to get the full time-chunked transcript.

Analyze and present:
1. All timestamps where "{topic}" is discussed
2. Context around each mention
3. The speaker's main points about this topic
4. A summary of the overall stance on "{topic}" """


# ── MCP Resources (Smithery quality) ────────────────────────────────────────


@mcp.resource("youtube://help")
def help_resource() -> str:
    """Help guide for the YouTube Transcript MCP server."""
    return """# YouTube Transcript MCP Server - Help Guide

## Available Tools

### get_transcript
Extract the full transcript from a YouTube video.
- Supports multiple languages (en, de, es, fr, ja, ko, zh, etc.)
- Three output formats: text, segments (with timestamps), or both
- Example: get_transcript(url="https://youtube.com/watch?v=VIDEO_ID", language="en", format="segments")

### search_transcript
Search for specific keywords within a video transcript.
- Case-insensitive search
- Shows surrounding context segments
- Example: search_transcript(url="VIDEO_ID", query="machine learning", context_segments=2)

### get_transcript_summary
Get the transcript organized in time chunks for analysis.
- Configurable chunk size (default: 5 minutes)
- Great for long videos
- Example: get_transcript_summary(url="VIDEO_ID", chunk_minutes=10)

### batch_transcripts
Process multiple videos at once (max 10).
- Returns preview of each transcript
- Example: batch_transcripts(urls=["VIDEO1", "VIDEO2"], language="en")

## Tips
- Use video IDs or full YouTube URLs
- Try different language codes if default transcript isn't available
- Use search_transcript to quickly find specific topics in long videos
- Use get_transcript_summary for videos over 20 minutes
"""

def main():
    settings = Settings()
    if settings.transport == Transport.STREAMABLE_HTTP:
        mcp.run(transport="streamable-http")
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
