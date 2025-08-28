from __future__ import annotations
import time, threading

class TokenBucket:
    def __init__(self, rate_per_s: float, capacity: int):
        self.rate = rate_per_s
        self.capacity = capacity
        self.tokens = capacity
        self.lock = threading.Lock()
        self.last = time.time()

    def take(self, n: int = 1) -> bool:
        with self.lock:
            now = time.time()
            self.tokens = min(self.capacity, self.tokens + (now - self.last) * self.rate)
            self.last = now
            if self.tokens >= n:
                self.tokens -= n
                return True
            return False
