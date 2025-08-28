"""
Lightweight audio cues for voice assistant UI feedback.
Provides simple beep sounds for state transitions.
"""
import os
import sys
import logging
import threading
from base64 import b64decode
import tempfile

# Embedded tiny WAV data (base64 encoded ~3KB, 50ms beeps)
LISTEN_BEEP_WAV_B64 = """UklGRoQDAABXQVZFZm10IBAAAAABAAEARKwAAESsAAABAAgAZGF0YWADAACAjaCNn42fjZ+NoI2gjaCNn42fjZ+NoI2gjaCNn42fjZ+NoI2gjaCNn42fjZ+NoI2gjaCNn42fjZ+NoI2gjaCNn42fjZ+NoI2gjaCNn42fjZ+NoI2gjaCNn42fjZ+NoI2gjaCNn42fjZ+NoI2gjaCNn42fjZ+NoI2gjaCNn42fjZ+NoI2gjaCNn42fjZ+NoI2gjaCNn42fjZ+NoI2gjaCNn42fjZ+NoI2gjaCNn42fjZ+NoI2gjaCNn42fjZ+NoI2gjaCNn42fjZ+NoI2gjaCNn42fjZ+NoI2gjaCNn42fjZ+NoI2gjaCNn42fjZ+NoI2gjaCNn42fjZ+NoI2gjaCNn42fjZ+NoI2gjaCNn42fjZ+NoI2gjaCNn42fjZ+NoI2gjaCNn42fjZ+NoI2gjaCNn42fjZ+NoI2gjaCNn42fjZ+NoI2gjaCNn42fjZ+NoI2gjaCNn42fjZ+NoI2gjaCNn42fjZ+NoI2gjaCNn42fjZ+NoI2gjaCNn42fjZ+NoI2gjaCNn42fjZ+NoI2gjaCNn42fjZ+NoI2gjaCNn42fjZ+NoI2gjaCNn42fjZ+NoI2gjaCNn42fjZ+NoI2gjaCNn42fjZ+NoI2gjaCNn42fjZ+NoI2gjaCNn42fjZ+NoI2gjaCNn42fjZ+NoI2gjaCNn42fjZ+NoI2gjaCNn42fjZ+NoI2gjaCNn42fjZ+NoI2gjaCNn42fjZ+NoI2gjaCNn42fjZ+NoI2gjaCNn42fjZ+NoI2gjaCNn42fjZ+NoI2gjaCNn42fjZ+NoI2gjaCNn42fjZ+NoI2gjaCNn42fjZ+NoI2gjaCNn42fjZ+NoI2gjaCNn42fjZ+NoI2gjaCNn42fjZ+NoI2gjaCNn42fjZ+NoI2gjaCNn42fjZ+NoI2gjaCNn42fjZ+NoI2gjaCNn42fjZ+NoI2gjaCNn42fjZ+NoI2gjaCNn42fjZ+NoI2gjaCNn42fjZ+NoI2gjaCNn42fjZ+NoI2gjaCNn42fjZ+NoI2g"""

LOADING_BEEP_WAV_B64 = """UklGRmwDAABXQVZFZm10IBAAAAABAAEARKwAAESsAAABAAgAZGF0YUgDAACApqiqqaqpqqmqqaqpqaipqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKio"""

# Temporary files for WAVs (created on demand)
_listen_wav_path = None
_loading_wav_path = None

def _init_beep_files():
    """Initialize the beep WAV files if needed"""
    global _listen_wav_path, _loading_wav_path
    
    if _listen_wav_path is None:
        try:
            # Create listen beep WAV
            fd, _listen_wav_path = tempfile.mkstemp(suffix='.wav')
            os.close(fd)
            with open(_listen_wav_path, 'wb') as f:
                f.write(b64decode(LISTEN_BEEP_WAV_B64))
                
            # Create loading beep WAV
            fd, _loading_wav_path = tempfile.mkstemp(suffix='.wav')
            os.close(fd)
            with open(_loading_wav_path, 'wb') as f:
                f.write(b64decode(LOADING_BEEP_WAV_B64))
        except Exception as e:
            logging.error(f"Failed to create beep files: {e}")
            _listen_wav_path = None
            _loading_wav_path = None

def play_beep_listening():
    """Play a quick beep indicating the system is listening"""
    # Try Windows-specific beep first (fastest, lowest latency)
    if sys.platform == 'win32':
        try:
            import winsound
            # Non-blocking beep (880Hz for 90ms)
            threading.Thread(
                target=winsound.Beep,
                args=(880, 90),
                daemon=True
            ).start()
            return
        except:
            pass
    
    # Fall back to WAV file if Windows beep not available
    _init_beep_files()
    if _listen_wav_path and os.path.exists(_listen_wav_path):
        try:
            from playsound import playsound
            # Non-blocking playback
            threading.Thread(
                target=playsound,
                args=(_listen_wav_path,),
                daemon=True
            ).start()
        except Exception as e:
            logging.debug(f"Could not play listening beep: {e}")
    
def play_beep_loading():
    """Play a quick beep indicating processing is starting"""
    # Try Windows-specific beep first (fastest, lowest latency)
    if sys.platform == 'win32':
        try:
            import winsound
            # Non-blocking beep (660Hz for 70ms)
            threading.Thread(
                target=winsound.Beep,
                args=(660, 70),
                daemon=True
            ).start()
            return
        except:
            pass
    
    # Fall back to WAV file if Windows beep not available
    _init_beep_files()
    if _loading_wav_path and os.path.exists(_loading_wav_path):
        try:
            from playsound import playsound
            # Non-blocking playback
            threading.Thread(
                target=playsound,
                args=(_loading_wav_path,),
                daemon=True
            ).start()
        except Exception as e:
            logging.debug(f"Could not play loading beep: {e}")