from __future__ import annotations
import os, json, time

LOG_PATH = os.path.join("logs", "telemetry.log")
os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)

def log_event(kind: str, payload: dict):
    rec = {"ts": time.time(), "kind": kind, "payload": payload}
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
