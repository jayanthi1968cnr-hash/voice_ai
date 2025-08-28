import os

def cadence_minutes() -> int:
    try:
        return int(os.getenv("LEARNER_CADENCE_MIN", "15"))
    except Exception:
        return 15

def max_pages_per_topic() -> int:
    try:
        return int(os.getenv("LEARNER_PAGES_PER_TOPIC", "3"))
    except Exception:
        return 3
