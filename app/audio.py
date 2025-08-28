import sounddevice as sd
import torch
import tempfile
import wave
import contextlib
import numpy as np
import logging
import time
import os  # Added missing os import

from config import cfg
from silero_vad import load_silero_vad, get_speech_timestamps
from shared_state import mic_enabled

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Load VAD once globally
try:
    vad_model = load_silero_vad()
    print("✅ Voice Activity Detection model loaded")
except Exception as e:
    logging.error(f"Failed to load VAD model: {e}")
    print(f"\x1b[31m❌ Failed to load VAD model: {e}\x1b[0m")
    vad_model = None

# Track global audio system state
_audio_system_busy = False
_last_audio_operation = 0

def reset_audio_system():
    """Force reset the audio system when stuck."""
    global _audio_system_busy
    
    try:
        # Release any resources sounddevice might be holding
        sd.stop()
        time.sleep(0.5)
        
        # Optional: try to terminate and reinitialize sounddevice
        try:
            from sounddevice import _terminate
            _terminate()
            time.sleep(1.0)
            print("🔄 Audio system forcefully reset")
        except:
            pass
        
        _audio_system_busy = False
        return True
    except Exception as e:
        logging.error(f"Failed to reset audio system: {e}")
        print(f"\x1b[31m❌ Failed to reset audio system: {e}\x1b[0m")
        return False

def record_until_silence(
    max_total_seconds: int = 30,
    silence_gap: float = 3.0,
    start_on_voice: bool = True,
    silence_tail_sec: float = 3.0,
    mic_gate=lambda: True
) -> str | None:
    """
    Start recording only when speech is detected.
    Stop after `silence_gap` seconds of silence.
    Cancel if no speech detected within `max_total_seconds`.
    Controlled by mic_gate() flag.
    """
    global _audio_system_busy, _last_audio_operation
    
    # Check if the audio system was recently used
    now = time.time()
    if now - _last_audio_operation < 2.0:
        print("⏳ Waiting for audio system to be ready...")
        time.sleep(2.0)  # Wait for system to settle
    
    # Mark system as busy
    _audio_system_busy = True
    _last_audio_operation = time.time()
    
    print("\x1b[36m🎤 Waiting for speech...\x1b[0m")
    sample_rate = 16000
    chunk_duration = 0.5  # in seconds
    chunk_samples = int(sample_rate * chunk_duration)
    buffer = []

    silence_start = None
    recording = False
    total_start = time.time()
    stream = None
    output_file = None
    
    try:
        # Create a new stream for this recording session
        # This avoids conflicts with the shared mic_stream
        stream = sd.InputStream(
            samplerate=sample_rate, 
            channels=1, 
            dtype="float32",
            latency='low',
            blocksize=int(sample_rate * 0.5)  # Larger block size for stability
        )
        stream.start()
    except Exception as e:
        logging.error(f"Failed to create recording stream: {e}")
        print(f"\x1b[31m❌ Could not start recording: {e}\x1b[0m")
        _audio_system_busy = False
        return None

    try:
        while True:
            # Safe way to check mic_gate (which might return an Event)
            should_record = False
            try:
                should_record = bool(mic_gate())
            except Exception as e:
                logging.error(f"Mic gate error: {e}")
                should_record = False
                
            if not should_record:
                time.sleep(0.1)  # Prevent CPU spinning
                continue  # skip this frame if mic should be off

            # Check if we've exceeded the max recording time
            if time.time() - total_start > max_total_seconds:
                if not recording:
                    print("\x1b[31m❌ No speech detected within time limit. Canceling...\x1b[0m")
                    return None
                else:
                    print("\x1b[33m⚠️ Reached maximum recording time. Finalizing...\x1b[0m")
                    break

            # Read audio data
            try:
                chunk, overflow = stream.read(chunk_samples)
                if overflow:
                    logging.warning("Audio buffer overflow during recording")
                audio_tensor = torch.from_numpy(chunk.squeeze())
            except Exception as e:
                logging.error(f"Error reading from stream: {e}")
                print(f"\x1b[31m⚠️ Recording error: {e}\x1b[0m")
                time.sleep(0.1)
                continue

            # Use Silero VAD to check for speech in chunk
            try:
                if vad_model is None:
                    # Fallback to simple amplitude detection if VAD model failed to load
                    has_speech = np.max(np.abs(chunk)) > 0.05
                    timestamps = [1] if has_speech else []
                else:
                    timestamps = get_speech_timestamps(audio_tensor, vad_model, sampling_rate=sample_rate)
            except Exception as e:
                logging.error(f"VAD error: {e}")
                timestamps = []

            # Process speech detection
            if timestamps:
                if not recording:
                    print("\x1b[32m🎙️ Speech detected. Recording started.\x1b[0m")
                recording = True
                buffer.append(audio_tensor)
                silence_start = None
            elif recording:
                buffer.append(audio_tensor)
                if silence_start is None:
                    silence_start = time.time()
                elif time.time() - silence_start > silence_tail_sec:
                    print("\x1b[33m🤫 Silence detected. Finalizing...\x1b[0m")
                    break

    except KeyboardInterrupt:
        print("\x1b[33m⏹️ Recording interrupted.\x1b[0m")
    except Exception as e:
        logging.exception("Recording error")
        print(f"\x1b[31m❌ Recording error: {e}\x1b[0m")
    finally:
        # Always clean up the stream
        if stream:
            try:
                stream.stop()
                stream.close()
            except Exception as e:
                logging.error(f"Error closing stream: {e}")

    # Release the audio system busy flag
    _audio_system_busy = False
    _last_audio_operation = time.time()
    
    # Don't process empty recordings
    if not buffer:
        print("\x1b[31m❌ No audio recorded.\x1b[0m")
        return None

    # Combine and save the recorded audio
    try:
        full_audio = torch.cat(buffer).unsqueeze(0)
        output_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        
        with contextlib.closing(wave.open(output_file.name, "wb")) as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            pcm = (full_audio.squeeze().numpy() * 32767).astype(np.int16).tobytes()
            wf.writeframes(pcm)
            
        return output_file.name
    except Exception as e:
        logging.exception("Failed to save audio")
        print(f"\x1b[31m❌ Failed to save recording: {e}\x1b[0m")
        # Attempt to clean up partial file
        if output_file and os.path.exists(output_file.name):
            try:
                os.remove(output_file.name)
            except:
                pass
        return None

def transcribe(path: str) -> str:
    """
    Run Whisper transcription on a WAV file and return cleaned text.
    """
    global _audio_system_busy, _last_audio_operation
    
    # Mark system as busy during transcription too (it may use audio resources)
    _audio_system_busy = True
    _last_audio_operation = time.time()
    
    if not path or not os.path.exists(path):
        print("\x1b[31m❌ Invalid audio file for transcription.\x1b[0m")
        _audio_system_busy = False
        return ""
        
    from faster_whisper import WhisperModel
    from text_utils import clean_stt_text

    try:
        print("\x1b[36m🧠 Transcribing audio...\x1b[0m")
        model = WhisperModel(cfg.WHISPER_SIZE, device="cpu", compute_type="int8")
        segments, _ = model.transcribe(path, vad_filter=False, language="en")
        text = " ".join(seg.text for seg in segments)
        clean_text = clean_stt_text(text)
        
        # Optional: Save transcription to file for debugging
        if getattr(cfg, "DEBUG_TRANSCRIPTION", False):
            try:
                with open(f"{path}.txt", "w") as f:
                    f.write(clean_text)
            except Exception as e:
                logging.error(f"Failed to save debug transcription: {e}")
                
        return clean_text
    except Exception as e:
        logging.exception("Whisper transcription failed")
        print(f"\x1b[31m❌ Transcription failed: {e}\x1b[0m")
        return ""
    finally:
        # Always clean up the temporary audio file
        try:
            if path and os.path.exists(path):
                os.remove(path)
        except Exception as e:
            logging.error(f"Failed to clean up audio file: {e}")
        
        # Release the audio system busy flag
        _audio_system_busy = False
        _last_audio_operation = time.time()