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
