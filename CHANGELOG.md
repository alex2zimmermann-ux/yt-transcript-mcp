# Changelog

## [1.0.0] - 2026-02-09

### Added
- Initial release
- `get_transcript` - Extract YouTube video transcripts with multi-language support
- `search_transcript` - Search keywords within transcripts with context
- `get_transcript_summary` - Time-chunked transcript analysis
- `batch_transcripts` - Process up to 10 videos at once
- Standalone mode (youtube-transcript-api) and Backend mode (VPS with Whisper fallback)
- In-memory TTL cache for performance
- Sliding window rate limiter
- MCP Prompts for video summarization, comparison, and key moment extraction
- Help resource with usage guide
- Docker support (standalone and backend profiles)
- Smithery marketplace deployment
