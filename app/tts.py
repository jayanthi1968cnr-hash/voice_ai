# app/tts.py
import uuid
import asyncio
import os
import logging
import threading
import time
import ctypes
import tempfile

import edge_tts
from playsound import playsound

from config import cfg

# Try to import sanitizer; fall back to a local one if missing
try:
    from text_utils import tts_sanitize
except Exception:
    import re
    def tts_sanitize(text: str) -> str:
        if not text:
            return ""
        t = re.sub(r"[\x00-\x1F\x7F]", " ", str(text))
        t = re.sub(r"\s+", " ", t).strip()
        return t[:2000]

from shared_state import mic_enabled, mic_stream

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# === Audio directory setup ===
AUDIO_DIR = os.path.abspath(getattr(cfg, "AUDIO_DIR", "") or os.path.join(os.getcwd(), "audio"))
os.makedirs(AUDIO_DIR, exist_ok=True)

# === Internal TTS state ===
_speaking_thread = None
_is_speaking = False
_audio_system_busy = threading.Event()
_last_tts_time = 0


def _reset_audio_device():
    """Attempt to reset the audio device (mainly helpful on Windows)."""
    try:
        import platform
        if platform.system() == "Windows":
            from ctypes import windll
            windll.winmm.mciSendStringW("close all", None, 0, None)
            time.sleep(0.6)
    except Exception as e:
        print(f"⚠️ Could not reset audio devices: {e}")
    time.sleep(0.6)


async def _tts_to_file(text: str, voice: str, outfile: str) -> bool:
    """Generate speech using Edge TTS into a file."""
    try:
        comm = edge_tts.Communicate(text, voice)
        await comm.save(outfile)
        return True
    except Exception as e:
        logging.error(f"Failed to generate speech: {e}")
        print(f"\x1b[31mTTS generation failed: {e}\x1b[0m")
        return False


def _stop_thread(thread: threading.Thread):
    """Forcefully stop a thread using ctypes (last resort)."""
    if not thread or not thread.is_alive():
        return
    try:
        tid = thread.ident
        exc = ctypes.py_object(SystemExit)
        res = ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_long(tid), exc)
        if res == 0:
            raise ValueError("Invalid thread ID")
        elif res > 1:
            ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_long(tid), None)
            raise SystemError("PyThreadState_SetAsyncExc failed")
    except Exception as e:
        logging.error(f"Failed to stop thread: {e}")


def speak(text: str, stop_flag: threading.Event = None):
    """
    Convert text to speech and play it while managing microphone state.
    Ensures the assistant doesn't hear itself.
    """
    global _speaking_thread, _is_speaking, _last_tts_time

    # Sanitize early
    txt = tts_sanitize(text)
    if not txt:
        return

    # Prevent overlapping TTS
    if _audio_system_busy.is_set():
        # wait briefly; if stuck, clear and try to recover
        waited = _audio_system_busy.wait(timeout=5.0)
        if not waited:
            _audio_system_busy.clear()
            _reset_audio_device()

    # Cooldown between TTS calls helps some backends/drivers
    now = time.time()
    since = now - _last_tts_time
    if since < 0.5:
        time.sleep(0.5 - since)

    _audio_system_busy.set()
    _last_tts_time = time.time()

    # Stop any ongoing speech
    if _speaking_thread and _speaking_thread.is_alive():
        _stop_thread(_speaking_thread)
        time.sleep(0.4)

    if stop_flag:
        stop_flag.clear()

    _is_speaking = True

    # Logical mute & try to stop mic stream
    mic_enabled.clear()
    if mic_stream and getattr(mic_stream, "active", False):
        try:
            mic_stream.stop()
            print("🔇 Mic stream stopped for TTS.")
        except Exception as e:
            print(f"\x1b[33m⚠️ Could not stop mic: {e}\x1b[0m")

    # small pause for audio subsystem
    time.sleep(0.2)

    def _play():
        global _is_speaking, _last_tts_time
        filename = None
        try:
            temp_dir = tempfile.gettempdir()
            unique_id = uuid.uuid4().hex
            filename = os.path.join(AUDIO_DIR, f"tts_{unique_id}.mp3")

            # Synthesize
            ok = asyncio.run(_tts_to_file(txt, cfg.VOICE, filename))
            if not ok or not os.path.exists(filename):
                print("\x1b[31m❌ Failed to generate speech audio\x1b[0m")
                return

            if stop_flag and stop_flag.is_set():
                print("🛑 TTS interrupted by stop flag")
                return

            # Play
            try:
                print("🔊 Playing TTS audio...")
                playsound(filename)
                print("✅ TTS playback completed")
            except Exception as e:
                logging.error(f"TTS playback failed: {e}")
                print(f"\x1b[31m❌ Audio playback failed: {e}\x1b[0m")
                _reset_audio_device()

        except Exception as e:
            logging.error(f"TTS process error: {e}")
            print(f"\x1b[31m❌ TTS process error: {e}\x1b[0m")
        finally:
            _is_speaking = False

            # Let audio system settle, then reset devices (Windows-friendly)
            time.sleep(0.3)
            _reset_audio_device()

            # Attempt to restart mic
            if mic_stream and not getattr(mic_stream, "active", False):
                try:
                    mic_stream.start()
                    print("🎙️ Mic stream restarted after TTS.")
                except Exception as e:
                    print(f"\x1b[33m⚠️ Failed to restart mic: {e}\x1b[0m")

            # Logical unmute regardless, so the loop can listen again
            mic_enabled.set()

            # Cleanup temp file
            if filename and not getattr(cfg, "KEEP_TTS", False) and os.path.exists(filename):
                try:
                    os.remove(filename)
                    # print("🧹 Cleaned up temporary audio file")
                except Exception as e:
                    print(f"⚠️ Could not remove temp file: {e}")

            _audio_system_busy.clear()
            _last_tts_time = time.time()

    _speaking_thread = threading.Thread(target=_play, name="TTS_Player", daemon=True)
    _speaking_thread.start()


def is_speaking() -> bool:
    return _is_speaking
