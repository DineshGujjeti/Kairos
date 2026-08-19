"""Tests for app.core.cache.TTLCache -- the generic in-process cache used
to fix the Root Cause Analysis performance problem (see
app.services.kpi.loader and app.services.root_cause.driver_detector)."""
import threading
import time

from app.core.cache import TTLCache


def test_set_and_get_roundtrip():
    cache = TTLCache(max_size=10, ttl_seconds=60)
    cache.set("a", 123)
    assert cache.get("a") == 123


def test_missing_key_returns_none():
    cache = TTLCache(max_size=10, ttl_seconds=60)
    assert cache.get("missing") is None


def test_ttl_expiry():
    cache = TTLCache(max_size=10, ttl_seconds=0.05)
    cache.set("a", 1)
    assert cache.get("a") == 1
    time.sleep(0.1)
    assert cache.get("a") is None


def test_lru_eviction_when_full():
    cache = TTLCache(max_size=2, ttl_seconds=60)
    cache.set("a", 1)
    cache.set("b", 2)
    cache.set("c", 3)  # evicts "a" (least recently used)
    assert cache.get("a") is None
    assert cache.get("b") == 2
    assert cache.get("c") == 3


def test_get_refreshes_lru_order():
    cache = TTLCache(max_size=2, ttl_seconds=60)
    cache.set("a", 1)
    cache.set("b", 2)
    cache.get("a")       # "a" is now most-recently-used
    cache.set("c", 3)    # should evict "b", not "a"
    assert cache.get("a") == 1
    assert cache.get("b") is None
    assert cache.get("c") == 3


def test_delete_removes_key():
    cache = TTLCache(max_size=10, ttl_seconds=60)
    cache.set("a", 1)
    cache.delete("a")
    assert cache.get("a") is None


def test_delete_prefix_removes_matching_keys_only():
    cache = TTLCache(max_size=10, ttl_seconds=60)
    cache.set(("dataset-1", "revenue"), "x")
    cache.set(("dataset-1", "cost"), "y")
    cache.set(("dataset-2", "revenue"), "z")
    cache.delete_prefix("('dataset-1'")
    assert cache.get(("dataset-1", "revenue")) is None
    assert cache.get(("dataset-1", "cost")) is None
    assert cache.get(("dataset-2", "revenue")) == "z"


def test_clear_empties_cache():
    cache = TTLCache(max_size=10, ttl_seconds=60)
    cache.set("a", 1)
    cache.set("b", 2)
    cache.clear()
    assert len(cache) == 0


def test_get_or_compute_calls_compute_once_on_miss():
    cache = TTLCache(max_size=10, ttl_seconds=60)
    calls = []

    def compute():
        calls.append(1)
        return "computed"

    result = cache.get_or_compute("key", compute)
    assert result == "computed"
    assert len(calls) == 1


def test_get_or_compute_uses_cache_on_second_call():
    """The core behaviour this whole module exists for: identical work
    requested twice must only actually run once."""
    cache = TTLCache(max_size=10, ttl_seconds=60)
    calls = []

    def compute():
        calls.append(1)
        return "expensive result"

    first = cache.get_or_compute("key", compute)
    second = cache.get_or_compute("key", compute)

    assert first == second == "expensive result"
    assert len(calls) == 1, "compute() must only run once across both calls"


def test_get_or_compute_concurrent_calls_dedupe():
    """Simulates two requests hitting the same uncached key at the same
    time (the exact /root-cause + /drivers page-load scenario) -- only
    one of them should actually run the expensive computation."""
    cache = TTLCache(max_size=10, ttl_seconds=60)
    calls = []
    call_lock = threading.Lock()

    def slow_compute():
        with call_lock:
            calls.append(1)
        time.sleep(0.05)
        return "result"

    results = []

    def worker():
        results.append(cache.get_or_compute("shared-key", slow_compute))

    threads = [threading.Thread(target=worker) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert all(r == "result" for r in results)
    assert len(calls) == 1, f"expected exactly 1 compute call, got {len(calls)}"
