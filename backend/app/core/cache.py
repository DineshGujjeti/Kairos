"""
Lightweight in-process TTL + LRU cache.

Root Cause Analysis (and, to a lesser extent, every other analytics
module) was re-reading the dataset file from disk and re-parsing it with
pandas on *every single request* -- and Root Cause additionally retrains
a RandomForestRegressor and runs mutual_info_regression from scratch
every time, even when the frontend calls both `/root-cause` and
`/drivers` for the same page load. That redundant work is what was
driving Root Cause Analysis to 20-30 seconds.

This is a deliberately simple, dependency-free cache -- no Redis, no
external service -- appropriate for this project's single-process
deployment (see docker-compose.yml: one backend container). If the
platform ever moves to multiple worker processes behind a load
balancer, this in-memory cache would need to move to a shared store
(Redis) since each process would otherwise have its own cold cache; that
is a deployment-topology change, not something this module needs to
anticipate today.

Usage
-----
    cache = TTLCache(max_size=64, ttl_seconds=300)

    value = cache.get(key)
    if value is None:
        value = expensive_computation()
        cache.set(key, value)

Or via the get_or_compute helper, which also protects against a cache
stampede on the *same* key from concurrent requests (only one caller
actually runs the compute function; others wait on it briefly rather
than each starting their own copy).
"""
from __future__ import annotations

import threading
import time
from collections import OrderedDict
from typing import Callable, Generic, Hashable, TypeVar

V = TypeVar("V")


class TTLCache(Generic[V]):
    """Thread-safe, size-bounded, TTL-expiring cache."""

    def __init__(self, max_size: int = 128, ttl_seconds: float = 300.0):
        self._max_size = max_size
        self._ttl = ttl_seconds
        self._store: "OrderedDict[Hashable, tuple[float, V]]" = OrderedDict()
        self._lock = threading.RLock()
        # One lock per in-flight key so concurrent requests for the same
        # uncached key don't all pay the full compute cost independently.
        self._key_locks: dict[Hashable, threading.Lock] = {}

    def get(self, key: Hashable) -> V | None:
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            expires_at, value = entry
            if expires_at < time.monotonic():
                del self._store[key]
                return None
            # Move to the end -> most-recently-used, for LRU eviction.
            self._store.move_to_end(key)
            return value

    def set(self, key: Hashable, value: V) -> None:
        with self._lock:
            self._store[key] = (time.monotonic() + self._ttl, value)
            self._store.move_to_end(key)
            while len(self._store) > self._max_size:
                self._store.popitem(last=False)  # evict least-recently-used

    def delete(self, key: Hashable) -> None:
        with self._lock:
            self._store.pop(key, None)

    def delete_prefix(self, prefix: str) -> None:
        """Delete every key whose str() starts with *prefix* -- used to
        invalidate every cache entry for a given dataset_id regardless
        of what else is baked into the rest of the key tuple."""
        with self._lock:
            to_delete = [k for k in self._store if str(k).startswith(prefix)]
            for k in to_delete:
                del self._store[k]

    def clear(self) -> None:
        with self._lock:
            self._store.clear()

    def __len__(self) -> int:
        with self._lock:
            return len(self._store)

    def get_or_compute(self, key: Hashable, compute: Callable[[], V]) -> V:
        """
        Return the cached value for *key*, computing and caching it via
        *compute* on a miss. Concurrent misses on the *same* key block on
        a per-key lock rather than each independently re-running compute
        (which is exactly the RandomForest-retrain-per-request scenario
        this module exists to avoid).
        """
        cached = self.get(key)
        if cached is not None:
            return cached

        with self._lock:
            key_lock = self._key_locks.setdefault(key, threading.Lock())

        with key_lock:
            # Re-check: another thread may have populated it while we
            # were waiting on key_lock.
            cached = self.get(key)
            if cached is not None:
                return cached
            value = compute()
            self.set(key, value)

        with self._lock:
            self._key_locks.pop(key, None)

        return value
