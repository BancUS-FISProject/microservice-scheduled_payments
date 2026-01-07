import time
import asyncio
from dataclasses import dataclass
from typing import Dict, Tuple, Optional

@dataclass(frozen=True)
class RateLimitResult:
    allowed: bool
    limit: int
    remaining: int
    reset_in_seconds: int

class InMemoryFixedWindowRateLimiter:
    def __init__(self, window_seconds: int):
        self.window_seconds = max(1, int(window_seconds))
        self._lock = asyncio.Lock()
        self._buckets: Dict[str, Tuple[int, int]] = {}

    def _window_start(self, now: int) -> int:
        return now - (now % self.window_seconds)

    async def allow(self, key: str, limit: int) -> RateLimitResult:
        now = int(time.time())
        wstart = self._window_start(now)
        reset_in = (wstart + self.window_seconds) - now

        limit = max(1, int(limit))
        if not key:
            key = "anonymous"

        async with self._lock:
            current = self._buckets.get(key)
            if current is None or current[0] != wstart:
                count = 1
                self._buckets[key] = (wstart, count)
                remaining = max(0, limit - count)
                return RateLimitResult(True, limit, remaining, reset_in)

            _, count = current
            if count >= limit:
                return RateLimitResult(False, limit, 0, reset_in)

            count += 1
            self._buckets[key] = (wstart, count)
            remaining = max(0, limit - count)
            return RateLimitResult(True, limit, remaining, reset_in)

    async def cleanup(self) -> None:
        now = int(time.time())
        wstart = self._window_start(now)
        threshold = wstart - (self.window_seconds * 2)

        async with self._lock:
            keys_to_delete = [k for k, (ws, _) in self._buckets.items() if ws < threshold]
            for k in keys_to_delete:
                self._buckets.pop(k, None)
