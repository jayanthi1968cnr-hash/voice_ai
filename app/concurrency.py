# ✅ Voice AI Hardening Plan — Phase 1 Implementation

# 1. Cancellation Token
# File: app/concurrency.py
import threading

class CancellationToken:
    def __init__(self):
        self._flag = threading.Event()
        self.reason = None

    def cancel(self, reason: str = ""):
        self.reason = reason or "cancelled"
        self._flag.set()

    def is_cancelled(self) -> bool:
        return self._flag.is_set()

    def wait(self, timeout: float) -> bool:
        return self._flag.wait(timeout)

class CancelScope:
    def __init__(self):
        self.token = CancellationToken()

    def __enter__(self):
        return self.token

    def __exit__(self, exc_type, exc, tb):
        self.token.cancel("scope exit")
        return False


# 2. Streaming TTS Start
# File: app/streaming.py
import time

def speak_while_generating(llm_iter, tts_start_after_tokens=20, tts_start_after_ms=400, token=None):
    buf = []
    t0 = time.time()
    started = False
    for tok in llm_iter:
        if token and token.is_cancelled():
            break
        buf.append(tok)
        if (not started) and (len(buf) >= tts_start_after_tokens or (time.time() - t0) * 1000 >= tts_start_after_ms):
            tts_start("".join(buf), token)
            started = True
        elif started:
            tts_append(tok, token)
    if not started and buf:
        tts_start("".join(buf), token)
    tts_finish(token)


# 3. Outbox Queue
# File: app/outbox.py
import queue, threading

class Outbox:
    def __init__(self):
        self.q = queue.Queue(maxsize=1)
        self.lock = threading.Lock()

    def submit(self, item):
        with self.lock:
            while not self.q.empty():
                try: self.q.get_nowait()
                except queue.Empty: break
            self.q.put(item)

    def take(self, timeout=None):
        return self.q.get(timeout=timeout)


# 4. Endpointing Improvements
# File: app/audio/endpoint.py
class EndpointPolicy:
    def __init__(self, base_tail_ms=1200, max_tail_ms=2800, energy_floor=0.015):
        self.base = base_tail_ms
        self.max = max_tail_ms
        self.energy = energy_floor

    def next_timeout(self, recent_energy, is_short_utterance):
        if recent_energy < self.energy:
            return self.base
        return self.max if not is_short_utterance else int(self.base * 0.8)


# 5. Device Watchdog
# File: app/audio/watchdog.py
import logging, time

class DeviceWatchdog:
    def __init__(self, reinit_fn, cooldown=2.0, max_attempts=3):
        self.reinit_fn = reinit_fn
        self.cooldown = cooldown
        self.max_attempts = max_attempts

    def guard(self, fn, *args, **kwargs):
        attempts = 0
        while True:
            try:
                return fn(*args, **kwargs)
            except Exception as e:
                attempts += 1
                logging.exception("Audio error; attempt %s/%s", attempts, self.max_attempts)
                if attempts >= self.max_attempts: raise
                time.sleep(self.cooldown)
                self.reinit_fn()


# 6. Tool Sandbox
# File: app/tools/sandbox.py
import signal, json, re
from contextlib import contextmanager

ALLOWED_DOMAINS = {"api.weather.gov", "news.ycombinator.com"}
MAX_OUTPUT_BYTES = 200_000

@contextmanager
def time_limit(seconds):
    def handler(signum, frame):
        raise TimeoutError("tool timed out")
    signal.signal(signal.SIGALRM, handler)
    signal.alarm(seconds)
    try:
        yield
    finally:
        signal.alarm(0)

def sanitize(s: str) -> str:
    s = re.sub(r"<script[\s\S]*?</script>", "", s, flags=re.I)
    return s

def is_allowed_url(url: str) -> bool:
    return any(url.split("/")[2].endswith(d) for d in ALLOWED_DOMAINS)

def run_tool(tool_fn, args, timeout_s=8):
    with time_limit(timeout_s):
        out = tool_fn(args)
    if isinstance(out, (dict, list)):
        out = json.dumps(out)[:MAX_OUTPUT_BYTES]
    else:
        out = str(out)[:MAX_OUTPUT_BYTES]
    return sanitize(out)


# 7. Safety Filters
# File: app/safety.py
import re

def moderate(text: str) -> tuple[bool, str]:
    banned = ["how to make a bomb", "child sexual"]
    for b in banned:
        if b in text.lower():
            return False, "I can’t help with that."
    return True, text

def redact_pii(text: str) -> str:
    text = re.sub(r"[\w.+-]+@[\w-]+\.[\w.-]+", "[email]", text)
    text = re.sub(r"\b\+?\d[\d\s()-]{7,}\b", "[phone]", text)
    return text
