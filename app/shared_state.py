import threading
import logging
import time
import sounddevice as sd
import json
import os

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Try to load audio device config
AUDIO_DEVICE_ID = None
try:
    if os.path.exists("audio_device.json"):
        with open("audio_device.json", "r") as f:
            config = json.load(f)
            AUDIO_DEVICE_ID = config.get("AUDIO_DEVICE_ID")
            print(f"📢 Using audio device: {config.get('AUDIO_DEVICE_NAME', 'Unknown')}")
except Exception as e:
    logging.error(f"Failed to load audio device config: {e}")

# Shared flags for microphone and assistant state
mic_enabled = threading.Event()  # Controls whether mic should be logically enabled
audio_system_lock = threading.RLock()  # Used to synchronize audio system operations

# Track when microphone was last started/stopped to prevent rapid toggling
last_mic_action = 0
MIN_ACTION_INTERVAL = 1.0  # Minimum seconds between mic start/stop operations

# Initialize as None first, then populate with create_mic_stream()
mic_stream = None

def initialize_portaudio():
    """Initialize PortAudio if not already initialized"""
    try:
        # Check if PortAudio is already initialized
        if hasattr(sd, '_initialized') and sd._initialized:
            print("✓ PortAudio is already initialized")
            return True
            
        # Initialize if needed
        sd._initialize()
        print("✅ PortAudio initialized successfully")
        return True
    except Exception as e:
        print(f"❌ Error initializing PortAudio: {e}")
        return False

def create_mic_stream():
    """
    Create a fresh microphone stream.
    Returns the created stream or None if failed.
    """
    global mic_stream
    
    with audio_system_lock:
        # Close existing stream if any
        if mic_stream:
            try:
                if hasattr(mic_stream, 'active') and mic_stream.active:
                    mic_stream.stop()
                mic_stream.close()
                print("🎙️ Closed existing mic stream.")
                time.sleep(0.5)  # Give system time to release resources
            except Exception as e:
                logging.error(f"Error closing existing mic stream: {e}")
        
        # Create new stream with minimal parameters
        try:
            # Create stream with explicit device ID if available
            new_stream = sd.InputStream(
                samplerate=16000,
                channels=1,
                dtype='float32',
                device=AUDIO_DEVICE_ID,  # Use configured device
                blocksize=4000  # Standard block size
            )
            print("✅ Created new mic stream")
            
            # Make sure it's not None
            if new_stream is None:
                raise ValueError("Stream was created but is None")
                
            return new_stream
            
        except Exception as e:
            logging.error(f"Failed to create mic stream: {e}")
            print(f"❌ Failed to initialize microphone: {e}")
            
            # Try an even simpler approach
            try:
                print("Trying alternate approach with minimal parameters...")
                new_stream = sd.InputStream(
                    samplerate=16000,
                    channels=1,
                    device=AUDIO_DEVICE_ID  # Just the essentials
                )
                if new_stream is None:
                    raise ValueError("Alternate stream was created but is None")
                    
                print("✅ Created mic stream with minimal parameters")
                return new_stream
            except Exception as e2:
                logging.error(f"Alternative approach also failed: {e2}")
                print(f"❌ Alternative initialization failed: {e2}")
            
            return None

def ensure_valid_mic_stream():
    """Check if mic_stream is valid and try to recreate if not"""
    global mic_stream
    
    with audio_system_lock:
        # Check if stream exists
        if mic_stream is None:
            print("⚠️ Mic stream is None, creating new stream")
            mic_stream = create_mic_stream()
            
        # Even if it exists, check if it's valid
        try:
            # Just accessing a property will raise an exception if invalid
            _ = hasattr(mic_stream, 'closed')
            return mic_stream is not None
        except Exception:
            print("⚠️ Invalid mic stream detected, recreating")
            mic_stream = create_mic_stream()
            return mic_stream is not None

def reset_mic_stream():
    """
    Force reset the microphone stream if it's in a bad state.
    Returns True if successful, False otherwise.
    """
    global mic_stream, last_mic_action
    
    # Check if we're resetting too frequently
    now = time.time()
    if now - last_mic_action < MIN_ACTION_INTERVAL:
        time.sleep(MIN_ACTION_INTERVAL)  # Force wait to avoid rapid toggling
    
    with audio_system_lock:
        # Try to force reset the audio system
        try:
            # Release any resources sounddevice might be holding
            sd.stop()
            time.sleep(0.5)
            
            # Try to terminate and reinitialize sounddevice (if available)
            try:
                from sounddevice import _terminate
                _terminate()
                time.sleep(0.5)  # Reduced from 1.0
                print("🔄 Audio system forcefully reset")
            except:
                pass
            
            # Create a fresh mic stream
            mic_stream = create_mic_stream()
            if mic_stream:
                # Don't automatically start it here, let the state machine handle that
                last_mic_action = time.time()
                return True
        except Exception as e:
            logging.error(f"Failed to reset mic stream: {e}")
            print(f"❌ Failed to reset microphone: {e}")
        
        return False

# Initialize PortAudio first
initialize_portaudio()

# Create the initial microphone stream
try:
    mic_stream = create_mic_stream()
    
    if mic_stream:
        print("🎙️ Shared microphone stream initialized successfully")
    else:
        print("⚠️ Voice assistant will run in degraded mode (no microphone)")
except Exception as e:
    logging.error(f"Error in shared_state.py initialization: {e}")
    print(f"❌ Failed to initialize mic_stream in shared_state.py: {e}")
    mic_stream = None