FROM python:3.12-slim

WORKDIR /app

RUN groupadd -r mcp && useradd -r -g mcp -d /app mcp

COPY pyproject.toml README.md ./
COPY src/ src/

RUN pip install --no-cache-dir .

USER mcp

ENTRYPOINT ["yt-transcript-mcp"]
