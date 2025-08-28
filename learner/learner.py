from __future__ import annotations
import threading
from learner.scheduler.job_loop import run_loop

_runner = None

def start(background: bool = True):
    """Start the constant learning loop."""
    global _runner
    def _go():
        print(" Constant Learning loop started.")
        run_loop()
    if background:
        if _runner and _runner.is_alive():
            print("ℹ Learner already running.")
            return
        _runner = threading.Thread(target=_go, name="LearnerLoop", daemon=True)
        _runner.start()
    else:
        _go()
