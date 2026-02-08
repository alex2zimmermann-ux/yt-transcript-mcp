"""Tests for cache logic."""

from yt_transcript_mcp.cache import TranscriptCache


class TestTranscriptCache:
    def test_set_and_get(self):
        cache = TranscriptCache(max_size=10, ttl=3600)
        data = {"video_id": "abc", "text": "hello"}
        cache.set("abc", "en", data)
        assert cache.get("abc", "en") == data

    def test_miss(self):
        cache = TranscriptCache(max_size=10, ttl=3600)
        assert cache.get("nonexistent", "en") is None

    def test_different_languages(self):
        cache = TranscriptCache(max_size=10, ttl=3600)
        data_en = {"video_id": "abc", "text": "hello"}
        data_de = {"video_id": "abc", "text": "hallo"}
        cache.set("abc", "en", data_en)
        cache.set("abc", "de", data_de)
        assert cache.get("abc", "en") == data_en
        assert cache.get("abc", "de") == data_de

    def test_stats_initial(self):
        cache = TranscriptCache(max_size=10, ttl=3600)
        stats = cache.stats()
        assert stats["size"] == 0
        assert stats["hits"] == 0
        assert stats["misses"] == 0

    def test_stats_after_operations(self):
        cache = TranscriptCache(max_size=10, ttl=3600)
        cache.set("abc", "en", {"text": "hi"})
        cache.get("abc", "en")  # hit
        cache.get("xyz", "en")  # miss
        stats = cache.stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["hit_rate"] == 50.0

    def test_max_size(self):
        cache = TranscriptCache(max_size=2, ttl=3600)
        cache.set("a", "en", {"text": "1"})
        cache.set("b", "en", {"text": "2"})
        cache.set("c", "en", {"text": "3"})
        # One of the first two should have been evicted
        assert cache.stats()["size"] == 2
