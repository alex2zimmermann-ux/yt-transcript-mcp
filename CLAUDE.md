# YouTube Transcript MCP Server

## Projekt
MCP-Server zum Extrahieren und Durchsuchen von YouTube-Video-Transkripten.

## Architektur
- **Strategy Pattern** mit zwei Modi:
  - `standalone`: Nutzt `youtube-transcript-api` direkt (leichtgewichtig, fuer Marketplaces)
  - `backend`: HTTP-Client zum bestehenden VPS-Service auf Port 8300 (volle Whisper-Fallback-Chain)
- **4 MCP Tools**: `get_transcript`, `search_transcript`, `get_transcript_summary`, `batch_transcripts`
- **Cache**: In-Memory TTLCache (cachetools)
- **Rate Limiting**: Sliding Window (deque)

## Wichtige Dateien
| Datei | Zweck |
|-------|-------|
| `src/yt_transcript_mcp/server.py` | FastMCP Server + Tool-Definitionen |
| `src/yt_transcript_mcp/config.py` | Pydantic Settings (YT_MCP_ Prefix) |
| `src/yt_transcript_mcp/providers/` | Standalone + Backend Provider |
| `tests/` | pytest Tests |

## Befehle
```bash
# Aktivieren
source .venv/bin/activate

# Tests
pytest tests/ -v --cov

# Server starten (stdio)
python -m yt_transcript_mcp

# MCP Inspector
npx @modelcontextprotocol/inspector python -m yt_transcript_mcp
```

## Env-Variablen
Alle mit `YT_MCP_` Prefix. Siehe `.env.example`.

## Referenz-Service
Der bestehende YT Transcript Service laeuft unter `/opt/yt-transcript/` auf Port 8300.
