# startup_check.py
import time
import logging

from config import cfg
from hotword import init_hotword

# Optional: only for listing devices without opening any stream
try:
    import sounddevice as sd
except Exception:
    sd = None


def _device_summary() -> str:
    """Return a short, safe summary of audio devices WITHOUT opening streams."""
    if sd is None:
        return "🎚️ sounddevice not available; skipping device summary."

    try:
        devices = sd.query_devices()
        def_dev = getattr(sd.default, "device", (None, None))
        in_idx, out_idx = (def_dev + (None, None))[:2]  # tolerate missing tuple

        def _name(idx):
            try:
                return devices[idx]["name"]
            except Exception:
                return "Unknown"

        lines = ["🎚️ Audio device summary (no streams opened):"]
        if in_idx is not None:
            lines.append(f"  • Default input:  #{in_idx}  { _name(in_idx) }")
        if out_idx is not None:
            lines.append(f"  • Default output: #{out_idx} { _name(out_idx) }")

        # Add first available input/output as a hint
        try:
            first_in = next((i for i, d in enumerate(devices) if d.get("max_input_channels", 0) > 0), None)
            first_out = next((i for i, d in enumerate(devices) if d.get("max_output_channels", 0) > 0), None)
            if first_in is not None:
                lines.append(f"  • First input-capable device:  #{first_in} {devices[first_in]['name']}")
            if first_out is not None:
                lines.append(f"  • First output-capable device: #{first_out} {devices[first_out]['name']}")
        except Exception:
            pass

        return "\n".join(lines)
    except Exception as e:
        return f"🎚️ Could not query devices: {e}"


def _check_hotword():
    print("🗣️ Testing hotword loading (no audio)...")
    try:
        count = init_hotword()
        if count and count > 0:
            print(f"✅ Loaded {count} hotword aliases.\n")
        else:
            print("⚠️ Hotword aliases returned 0 (verify config).\n")
    except Exception as e:
        print(f"❌ Hotword init failed: {e}\n")


def _check_firestore_if_enabled():
    if not getattr(cfg, "FIRESTORE_ENABLED", False):
        return
    try:
        from firebase_db import load_facts
        _ = load_facts()
        print("☁️ Firestore: ✅ Access confirmed.\n")
    except Exception as e:
        print(f"❌ Firestore: Connection failed - {e}\n")


def run_all_checks():
    """
    Lightweight startup checks:
    - NO TTS playback
    - NO microphone recording
    - NO audio device resets
    - Just hotword + optional Firestore + device listing
    """
    if not getattr(cfg, "STARTUP_CHECKS", False):
        # Completely skip when disabled
        return

    print("\n🧪 Running Voice Assistant Startup Check (lightweight)…\n")

    # Hotword (pure config/code path)
    _check_hotword()

    # Device list (never opens streams)
    print(_device_summary() + "\n")

    # Optional Firestore
    _check_firestore_if_enabled()

    print("✅ All checks complete.\n")


if __name__ == "__main__":
    run_all_checks()
