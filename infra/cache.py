from __future__ import annotations
import time, functools

def memo_ttl(ttl_s: int = 60):
    def deco(fn):
        cache = {}
        @functools.wraps(fn)
        def wrap(*a, **k):
            key = (a, tuple(sorted(k.items())))
            now = time.time()
            if key in cache:
                v, ts = cache[key]
                if now - ts < ttl_s:
                    return v
            v = fn(*a, **k)
            cache[key] = (v, now)
            return v
        return wrap
    return deco
