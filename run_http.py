"""HTTP runner for MCP server (Smithery / remote deployment)."""
import sys, os
os.environ["YT_MCP_MODE"] = "standalone"

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.server import TransportSecuritySettings
from yt_transcript_mcp.server import (
    app_lifespan,
    get_transcript,
    search_transcript,
    get_transcript_summary,
    batch_transcripts,
    summarize_video,
    compare_videos,
    find_key_moments,
    help_resource,
    TOOL_ANNOTATIONS,
)

server = FastMCP(
    "YouTube Transcript",
    instructions="Extract and search YouTube video transcripts",
    lifespan=app_lifespan,
    host="0.0.0.0",
    port=8401,
    transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
)

# Register tools with annotations
server.tool(annotations=TOOL_ANNOTATIONS)(get_transcript)
server.tool(annotations=TOOL_ANNOTATIONS)(search_transcript)
server.tool(annotations=TOOL_ANNOTATIONS)(get_transcript_summary)
server.tool(annotations=TOOL_ANNOTATIONS)(batch_transcripts)

# Register prompts
server.prompt()(summarize_video)
server.prompt()(compare_videos)
server.prompt()(find_key_moments)

# Register resources
server.resource("youtube://help")(help_resource)

server.run(transport="streamable-http")
