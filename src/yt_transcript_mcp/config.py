"""Configuration via environment variables."""

from enum import Enum
from pydantic_settings import BaseSettings


class Mode(str, Enum):
    STANDALONE = "standalone"
    BACKEND = "backend"


class Transport(str, Enum):
    STDIO = "stdio"
    STREAMABLE_HTTP = "streamable-http"


class Settings(BaseSettings):
    model_config = {"env_prefix": "YT_MCP_"}

    mode: Mode = Mode.STANDALONE
    backend_url: str = "http://148.230.105.106:8300"
    backend_api_key: str = ""
    cache_max_size: int = 100
    cache_ttl_seconds: int = 3600
    rate_limit_per_minute: int = 30
    transport: Transport = Transport.STDIO


settings = Settings()
