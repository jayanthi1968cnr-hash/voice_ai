# app/main.py
import os
import sys
import time
import logging
import threading
from enum import Enum, auto
from datetime import datetime

# Ensure root path for orchestrator import works
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import cfg
from audio import record_until_silence, transcribe
from hotword import init_hotword
from tts import speak, is_speaking
from logging_utils import log_turn, save_context, load_context, should_sleep
from listener_interrupt import start_interrupt_listener
from shared_state import mic_enabled, mic_stream
from orchestrator.turn import handle_turn

# -----------------------------
# Minimal state machine
# -----------------------------
class State(Enum):
    IDLE = auto()
    LISTENING = auto()
    PROCESSING = auto()
    SPEAKING = auto()

state_lock = threading.RLock()
assistant_busy = threading.Event()
stop_tts_now = threading.Event()
current_state: State | None = None
last_state_change = 0.0

def _startup_beep():
    try:
        import platform
        if platform.system() == "Windows":
            import winsound
            winsound.Beep(880, 90)
        else:
            print("\a", end="", flush=True)
    except Exception:
        pass

def set_state(new_state: State):
    global current_state, last_state_change
    with state_lock:
        now = time.time()
        if current_state == new_state:
            return
        if current_state and now - last_state_change < 0.5:
            time.sleep(0.5)

        current_state, last_state_change = new_state, now
        print(f"\x1b[35m\ud83d\udd04 State change: {new_state.name}\x1b[0m")

        if new_state in (State.PROCESSING, State.SPEAKING):
            assistant_busy.set()
            mic_enabled.clear()
            if mic_stream and getattr(mic_stream, "active", False):
                try:
                    mic_stream.stop()
                    print("\ud83d\udcf4 Mic stream stopped.")
                except Exception:
                    pass

        elif new_state == State.LISTENING:
            assistant_busy.clear()
            time.sleep(1.0)
            if mic_stream and not getattr(mic_stream, "active", False):
                try:
                    mic_stream.start()
                    print("\ud83c\udfa4 Mic stream started.")
                except Exception:
                    pass
            mic_enabled.set()
            _startup_beep()

        elif new_state == State.IDLE:
            assistant_busy.clear()
            mic_enabled.clear()
            if mic_stream and getattr(mic_stream, "active", False):
                try:
                    mic_stream.stop()
                    print("\ud83d\ude34 Mic stream stopped (idle).")
                except Exception:
                    pass

def _startup_banner():
    print(f"\x1b[32m\u2705 Voice Assistant '{cfg.HOTWORD.title()}' Ready!\x1b[0m")
    print("\x1b[2mSay the hotword to wake me. Say 'sleep' to pause or 'quit' to exit.\x1b[0m")
    print(f"\x1b[2mModel: {cfg.GROQ_MODEL} via Groq API\x1b[0m")
    alias_count = init_hotword()
    print(f"\x1b[2mLoaded {alias_count} hotword aliases for '{cfg.HOTWORD}'.\x1b[0m")

def _say(text: str):
    stop_tts_now.clear()
    msg = (text or "").strip()
    print(f"\x1b[36m{cfg.HOTWORD.title()}:\x1b[0m {msg}")
    log_turn("assistant", msg)

    set_state(State.SPEAKING)
    speak(msg, stop_flag=stop_tts_now)

    time.sleep(0.4)
    while is_speaking():
        time.sleep(0.1)

    time.sleep(0.6)
    set_state(State.LISTENING)

# -----------------------------
# Main loop
# -----------------------------
def main():
    os.makedirs("logs", exist_ok=True)
    logging.basicConfig(
        filename="logs/assistant.log",
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )
    logging.info("=== Voice Assistant Starting ===")

    try:
        _startup_banner()

        if mic_stream:
            print("\ud83c\udfa4 Mic stream ready.")
        else:
            print("\x1b[31m\u274c Mic stream not available. Degraded mode.\x1b[0m")

        start_interrupt_listener(stop_tts_now)
        history = load_context()
        set_state(State.LISTENING)

        consecutive_errors = 0
        last_success = time.time()

        while True:
            try:
                if not mic_enabled.is_set():
                    time.sleep(0.2)
                    continue

                path = record_until_silence(
                    max_total_seconds=30,
                    start_on_voice=True,
                    silence_tail_sec=3.0,
                    mic_gate=lambda: mic_enabled.is_set(),
                )
                if not path:
                    continue

                set_state(State.PROCESSING)
                user_text = transcribe(path)
                if not user_text:
                    set_state(State.LISTENING)
                    continue

                log_turn("user", user_text)
                print(f"\x1b[32mYou said:\x1b[0m {user_text}")

                low = user_text.lower().strip()
                if low in ("quit", "exit"):
                    print(f"\n\x1b[31m\ud83d\udc4b {cfg.HOTWORD.title()} shutting down. Goodbye!\x1b[0m")
                    break
                if should_sleep(user_text):
                    set_state(State.IDLE)
                    print(f"\x1b[35m\ud83d\udecc Going to sleep. Say '{cfg.HOTWORD}' to wake me.\x1b[0m")
                    continue

                result = handle_turn(user_text, history)
                reply_text = getattr(result, "reply", None) or (result if isinstance(result, str) else "")
                if not reply_text:
                    reply_text = "Sorry, I couldn't get a response."

                _say(reply_text)

                history.append({"role": "user", "content": user_text})
                history.append({"role": "assistant", "content": reply_text})
                history[:] = history[-(cfg.CONTEXT_TURNS * 2):]
                save_context(history)

                consecutive_errors = 0
                last_success = time.time()

            except KeyboardInterrupt:
                print(f"\n\x1b[31m\ud83d\udc4b {cfg.HOTWORD.title()} shutting down. Goodbye!\x1b[0m")
                break
            except Exception as e:
                consecutive_errors += 1
                logging.exception(f"Loop error ({consecutive_errors})")
                print(f"\x1b[31m\u274c Unexpected error ({consecutive_errors}): {e}\x1b[0m")

                if consecutive_errors < 5:
                    _say("Sorry, something went wrong. I'll keep listening.")
                if consecutive_errors >= 5 or (time.time() - last_success > 300):
                    print("\x1b[31m\u26a0\ufe0f Too many errors or timeout; continuing...\x1b[0m")
                    consecutive_errors = 0

                set_state(State.LISTENING)
                time.sleep(1)

    finally:
        logging.info("=== Voice Assistant Shutting Down ===")
        stop_tts_now.set()
        time.sleep(0.5)
        if mic_stream:
            try:
                mic_stream.stop()
                print("\ud83c\udfa4 Mic stream stopped cleanly.")
            except Exception as e:
                print(f"\x1b[31mError closing mic stream: {e}\x1b[0m")
        logging.info("Assistant shutdown complete")

if __name__ == "__main__":
    main()
