"""In-memory TTL cache for transcripts."""

from cachetools import TTLCache


class TranscriptCache:
    def __init__(self, max_size: int = 100, ttl: int = 3600):
        self._cache: TTLCache = TTLCache(maxsize=max_size, ttl=ttl)
        self._hits = 0
        self._misses = 0

    def _key(self, video_id: str, language: str) -> str:
        return f"{video_id}:{language}"

    def get(self, video_id: str, language: str) -> dict | None:
        key = self._key(video_id, language)
        result = self._cache.get(key)
        if result is not None:
            self._hits += 1
        else:
            self._misses += 1
        return result

    def set(self, video_id: str, language: str, data: dict) -> None:
        key = self._key(video_id, language)
        self._cache[key] = data

    def stats(self) -> dict:
        return {
            "size": len(self._cache),
            "max_size": self._cache.maxsize,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": round(self._hits / max(self._hits + self._misses, 1) * 100, 1),
        }
