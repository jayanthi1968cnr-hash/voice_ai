"""
Emergency audio system reset utility.
This provides a "nuke from orbit" approach when normal initialization fails.
"""
import time
import sys
import os
import importlib

def force_reload_audio():
    """
    Force Python to completely reload sounddevice and all audio components
    """
    # List of modules to reload
    audio_modules = [
        'sounddevice', 
        'shared_state', 
        'audio', 
        'listener_interrupt'
    ]
    
    print("🧨 PERFORMING EMERGENCY AUDIO SYSTEM RESET")
    
    # First, unload the modules
    for module_name in audio_modules:
        if module_name in sys.modules:
            print(f"  - Unloading {module_name}")
            del sys.modules[module_name]
    
    # Wait for system to settle
    time.sleep(1.0)
    
    # Then reload them
    for module_name in audio_modules:
        try:
            print(f"  - Reloading {module_name}")
            importlib.import_module(module_name)
        except Exception as e:
            print(f"  ⚠️ Could not reload {module_name}: {e}")
    
    # Get the sounddevice module and try a complete restart
    import sounddevice as sd
    
    # Don't call terminate if not needed
    try:
        # Only try to re-initialize without terminating first
        sd._initialize()
        print("✅ Successfully reinitialized PortAudio")
        return True
    except Exception as e:
        print(f"❌ Failed to reinitialize PortAudio: {e}")
        return False

if __name__ == "__main__":
    # Can be run directly as a utility
    success = force_reload_audio()
    print(f"Audio system reset {'succeeded' if success else 'failed'}")