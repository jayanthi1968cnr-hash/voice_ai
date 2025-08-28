import threading
import time
import numpy as np
import logging
import sounddevice as sd

from shared_state import mic_enabled, mic_stream
from tts import is_speaking

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Detection settings
ENERGY_THRESHOLD = 0.05  # Lower values = more sensitive
CHECK_INTERVAL = 0.2  # How often to check for interruptions (seconds)
CONSECUTIVE_FRAMES = 2  # How many consecutive frames must exceed threshold

# Track interruption state
_interrupt_thread = None
_thread_should_exit = threading.Event()

def start_interrupt_listener(stop_tts_flag):
    """
    Start a thread to listen for voice while TTS is playing to allow interruptions.
    Uses simple amplitude detection for better reliability.
    """
    global _interrupt_thread, _thread_should_exit
    
    # Clean up any existing thread
    if _interrupt_thread and _interrupt_thread.is_alive():
        _thread_should_exit.set()
        time.sleep(0.5)
    
    # Reset the exit flag
    _thread_should_exit.clear()
    
    # Start a new thread
    _interrupt_thread = threading.Thread(
        target=_listener, 
        args=(stop_tts_flag,),
        daemon=True,
        name="InterruptListener"
    )
    _interrupt_thread.start()
    print("🎧 Voice interrupt listener started...")
    return _interrupt_thread

def _listener(stop_flag):
    """
    Listen for voice while TTS is playing and set the stop flag if detected.
    Uses simple amplitude detection rather than VAD for reliability.
    """
    sample_rate = 16000
    chunk_samples = int(sample_rate * CHECK_INTERVAL)
    high_energy_frames = 0
    
    try:
        while not _thread_should_exit.is_set():
            # Only check for interruptions when TTS is active
            # and mic is muted (logical state)
            if is_speaking() and not mic_enabled.is_set():
                try:
                    # Safely check if mic stream is available
                    if mic_stream is None:
                        time.sleep(CHECK_INTERVAL)
                        continue
                    
                    # Safely check if mic is active without using .active property
                    # which can fail with "PortAudio not initialized"
                    try:
                        mic_is_active = getattr(mic_stream, 'active', False)
                    except Exception:
                        # If we can't check .active property, assume inactive
                        time.sleep(CHECK_INTERVAL)
                        continue
                    
                    if not mic_is_active:
                        time.sleep(CHECK_INTERVAL)
                        continue
                    
                    # Try to read audio data
                    try:
                        data, overflow = mic_stream.read(chunk_samples)
                        
                        # Calculate energy level (root mean square)
                        energy = np.sqrt(np.mean(np.square(data)))
                        
                        # Check if energy exceeds threshold
                        if energy > ENERGY_THRESHOLD:
                            high_energy_frames += 1
                            if high_energy_frames >= CONSECUTIVE_FRAMES:
                                # Interrupt detected
                                print(f"🛑 Voice detected during TTS (energy={energy:.4f}). Interrupting...")
                                stop_flag.set()
                                # Reset counter and wait to avoid multiple triggers
                                high_energy_frames = 0
                                time.sleep(0.5)
                        else:
                            # Decay counter if below threshold
                            high_energy_frames = max(0, high_energy_frames - 1)
                    
                    except Exception as e:
                        # Handle specific error types
                        if "not initialized" in str(e):
                            # PortAudio not initialized - just wait
                            time.sleep(0.5)
                        elif "busy" in str(e).lower() or "device unavailable" in str(e).lower():
                            # Device busy or unavailable - wait longer
                            time.sleep(1.0)
                        else:
                            # Other errors - log and continue
                            logging.warning(f"Audio read error in interrupt listener: {e}")
                            time.sleep(0.2)
                except Exception as e:
                    # Error in outer processing logic
                    logging.warning(f"Interrupt detection error: {e}")
                    time.sleep(0.5)
            else:
                # Not speaking or mic is logically enabled
                time.sleep(CHECK_INTERVAL)
                high_energy_frames = 0  # Reset counter
                
    except Exception as e:
        logging.error(f"Interrupt listener crashed: {e}", exc_info=True)
        print(f"❌ Interrupt listener crashed: {e}")
        
        # Try to restart after a delay, but only if not exiting
        if not _thread_should_exit.is_set():
            time.sleep(2.0)
            print("🔄 Attempting to restart interrupt listener...")
            threading.Thread(
                target=start_interrupt_listener,
                args=(stop_flag,),
                daemon=True
            ).start()

def shutdown_interrupt_listener():
    """Gracefully shut down the interrupt listener thread."""
    global _thread_should_exit
    _thread_should_exit.set()
    if _interrupt_thread and _interrupt_thread.is_alive():
        _interrupt_thread.join(timeout=1.0)
        print("✓ Interrupt listener shut down")