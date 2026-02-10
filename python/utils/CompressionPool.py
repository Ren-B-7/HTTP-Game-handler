"""
Cached compression pool for gzip compression.

This module provides a simple cached compression system for efficiently
compressing static files that are served repeatedly. Instead of compressing
the same file on every request, this module caches compressed results for
significant performance improvements.

Classes:
    SimpleCachedCompressor: Thread-safe cached gzip compressor


Author: Renier Barnard (renier52147@gmail.com/ renierb@axxess.co.za)
"""

import gzip
import hashlib
import threading
from typing import Optional


class SimpleCachedCompressor:
    """
    Thread-safe cached gzip compressor for repeated data.

    This class maintains an in-memory cache of compressed data, keyed by
    either a provided cache key (e.g., filepath) or an MD5 hash of the content.

    Attributes:
        _cache (dict): Cache storage {full_key: compressed_bytes}
        _max_cache_size (int): Maximum number of items to cache
        _lock (threading.Lock): Protects cache and stats from concurrent access
        _stats (dict): Statistics (hits, misses, compressions)
    """

    def __init__(self, max_cache_size: int = 256):
        """
        Initialize cached compressor.

        Args:
            max_cache_size: Maximum number of compressed items to cache
                          (default: 256). When exceeded, oldest items are evicted.

        Note:
            Choosing max_cache_size:
            - Too small: More cache misses, more CPU usage
            - Too large: More memory usage
            - Rule of thumb: Set to ~2x the number of unique files you serve
        """
        self._cache = {}  # {full_key: compressed_bytes}
        self._max_cache_size = max_cache_size
        self._lock = threading.Lock()
        self._stats = {"hits": 0, "misses": 0, "compressions": 0}

    def compress(
        self, data: bytes, compresslevel: int = 6, cache_key: Optional[str] = None
    ) -> bytes:
        """
        Compress data with caching.

        This method first checks the cache for previously compressed data.
        On cache miss, it compresses the data and stores it for future requests.
        Different compression levels are cached differently

        Args:
            data: Raw bytes to compress
            compresslevel: gzip compression level (1-9)
                         1 = fastest, largest output
                         6 = balanced (default)
                         9 = slowest, smallest output
            cache_key: Optional key for caching (e.g., filepath)
                      If None, MD5 hash of data is used

        Returns:
            bytes: Compressed data

        """
        # Generate cache key if not provided
        # Using MD5 hash for content-based caching
        if cache_key is None:
            cache_key = hashlib.md5(data).hexdigest()

        # Full cache key includes compression level
        # This allows caching the same file at different compression levels
        full_key = f"{cache_key}:{compresslevel}"

        # Check cache (fast path)
        with self._lock:
            if full_key in self._cache:
                self._stats["hits"] += 1
                return self._cache[full_key]

            self._stats["misses"] += 1

        # Cache miss - compress the data (outside lock to avoid blocking)
        compressed = gzip.compress(data, compresslevel=compresslevel)
        self._stats["compressions"] += 1

        # Store in cache
        with self._lock:
            # Remove the first (oldest) item to make room
            if len(self._cache) >= self._max_cache_size:
                # next(iter(dict)) returns the first key (insertion order preserved)
                self._cache.pop(next(iter(self._cache)))

            self._cache[full_key] = compressed

        return compressed

    def clear_cache(self):
        """
        Clear the compression cache.

        This is useful when:
        - Static files have been updated
        - Memory usage needs to be reduced
        - Server is reloading configuration
        """
        with self._lock:
            self._cache.clear()

    def get_stats(self) -> dict:
        """
        Get compression statistics for monitoring.

        Returns:
            dict: Statistics including:
                - hits: Number of cache hits
                - misses: Number of cache misses
                - compressions: Total compressions performed
                - cache_size: Current number of cached items
                - hit_rate: Cache hit percentage
                - max_cache_size: Maximum cache capacity
        """
        with self._lock:
            total = self._stats["hits"] + self._stats["misses"]
            hit_rate = (self._stats["hits"] / total * 100) if total > 0 else 0

            return {
                **self._stats,  # hits, misses, compressions
                "cache_size": len(self._cache),
                "hit_rate": f"{hit_rate:.1f}%",
                "max_cache_size": self._max_cache_size,
            }
