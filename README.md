# YouTube Transcript MCP Server

An MCP (Model Context Protocol) server that extracts, searches, and analyzes YouTube video transcripts. Works with Claude Desktop, Cursor, and any MCP-compatible client.

## Features

- **Get Transcript** - Extract full transcript from any YouTube video
- **Search Transcript** - Find specific keywords with surrounding context
- **Transcript Summary** - Get time-chunked transcript for easier analysis
- **Batch Processing** - Process up to 10 videos at once

## Installation

### pip (recommended)

```bash
pip install yt-transcript-mcp
```

### From source

```bash
git clone https://github.com/alexruco/yt-transcript-mcp
cd yt-transcript-mcp
pip install .
```

## Configuration

### Claude Desktop

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "youtube-transcript": {
      "command": "yt-transcript-mcp",
      "env": {
        "YT_MCP_MODE": "standalone"
      }
    }
  }
}
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `YT_MCP_MODE` | `standalone` | `standalone` or `backend` |
| `YT_MCP_BACKEND_URL` | `http://localhost:8300` | Backend service URL |
| `YT_MCP_BACKEND_API_KEY` | - | API key for backend |
| `YT_MCP_CACHE_MAX_SIZE` | `100` | Max cache entries |
| `YT_MCP_CACHE_TTL_SECONDS` | `3600` | Cache TTL in seconds |
| `YT_MCP_RATE_LIMIT_PER_MINUTE` | `30` | Rate limit |
| `YT_MCP_TRANSPORT` | `stdio` | `stdio` or `streamable-http` |

## Modes

### Standalone (default)
Uses `youtube-transcript-api` directly. Lightweight, no external dependencies. Best for marketplace deployment.

### Backend
Connects to a running transcript service (FastAPI) that supports cookies, yt-dlp, and Whisper fallback. Best for premium/self-hosted usage.

## Tools

### `get_transcript`
Get the transcript of a YouTube video.

**Parameters:**
- `url` (required) - YouTube URL or video ID
- `language` (optional, default: "en") - Language code
- `format` (optional, default: "text") - "text", "segments", or "both"

### `search_transcript`
Search for keywords in a video transcript.

**Parameters:**
- `url` (required) - YouTube URL or video ID
- `query` (required) - Search term
- `language` (optional, default: "en")
- `context_segments` (optional, default: 1) - Surrounding segments to include

### `get_transcript_summary`
Get transcript in time chunks for analysis.

**Parameters:**
- `url` (required) - YouTube URL or video ID
- `language` (optional, default: "en")
- `chunk_minutes` (optional, default: 5)

### `batch_transcripts`
Process multiple videos at once.

**Parameters:**
- `urls` (required) - List of YouTube URLs or IDs (max 10)
- `language` (optional, default: "en")

## Docker

```bash
# Standalone
docker compose --profile standalone up

# Backend
YT_MCP_BACKEND_API_KEY=your-key docker compose --profile backend up
```

## Development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest tests/ -v --cov
```

## License

MIT
