# app/config.py

import os
from dotenv import load_dotenv

# ✅ Load .env file at the start
load_dotenv()

def _getenv_list(name: str, default: str = "") -> list[str]:
    raw = os.getenv(name, default) or ""
    raw = raw.replace("\n", " ")
    parts = [p.strip() for p in raw.split(",")]
    return [p for p in parts if p]

class Config:
    # -----------------------------
    # Groq API (✅ Primary LLM)
    # -----------------------------
    GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
    GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant").strip()
    LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.3"))
    LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "512"))
    LLM_CONNECT_TIMEOUT = float(os.getenv("LLM_CONNECT_TIMEOUT", "5"))
    LLM_READ_TIMEOUT = float(os.getenv("LLM_READ_TIMEOUT", "180"))
    LLM_HEALTHCHECK_SECONDS = int(os.getenv("LLM_HEALTHCHECK_SECONDS", "10"))
    SYSTEM_PROMPT = os.getenv("SYSTEM_PROMPT", "You are a concise, helpful assistant.")

    # -----------------------------
    # Optional Hugging Face Backup (❌ Disable if unused)
    # -----------------------------
    SPACE_URL = os.getenv("SPACE_URL", "").strip()
    HF_TOKEN = os.getenv("HF_TOKEN", "").strip()
    LLM_ROUTE = os.getenv("LLM_ROUTE", "").strip()

    # -----------------------------
    # Audio / STT / TTS
    # -----------------------------
    WHISPER_SIZE = os.getenv("WHISPER_SIZE", "tiny")
    SAMPLE_RATE = int(os.getenv("SAMPLE_RATE", "16000"))
    MAX_TURN_RECORD_SECONDS = int(os.getenv("MAX_TURN_RECORD_SECONDS", "15"))
    RECORD_DEVICE = os.getenv("RECORD_DEVICE", "").strip()
    VOICE = os.getenv("VOICE", "en-IE-EmilyNeural")
    AUDIO_DIR = os.getenv("AUDIO_DIR", "audio").strip()
    # 🔄 Changed default to True so we skip deleting TTS temp files (reduces lag)
    KEEP_TTS = os.getenv("KEEP_TTS", "1").strip().lower() in ("1", "true", "yes")

    CHANNELS = int(os.getenv("CHANNELS", "1"))  # mono
    DTYPE = os.getenv("DTYPE", "float32").strip()  # sounddevice dtype
    VAD_SAMPLING_RATE = int(os.getenv("VAD_SAMPLING_RATE", "16000"))

    # -----------------------------
    # Hotword & Aliases
    # -----------------------------
    HOTWORD = os.getenv("HOTWORD", "irish").strip().lower()
    ACCENT_PRESET = os.getenv("ACCENT_PRESET", "").strip().lower()
    HOTWORD_MAX_ALIASES = int(os.getenv("HOTWORD_MAX_ALIASES", "-1"))
    HOTWORD_ALIAS_HARD_CAP = int(os.getenv("HOTWORD_ALIAS_HARD_CAP", "2000"))
    HOTWORD_ALIASES_PATH = os.getenv("HOTWORD_ALIASES_PATH", "hotword_aliases.json").strip()
    HOTWORD_FUZZY_THRESH = float(os.getenv("HOTWORD_FUZZY_THRESH", "0.74"))

    HOTWORD_SEED_ALIASES = _getenv_list("HOTWORD_SEED_ALIASES")
    ALIASES = _getenv_list("ALIASES")
    ALL_SEED_ALIASES = list(dict.fromkeys(HOTWORD_SEED_ALIASES + ALIASES))

    # -----------------------------
    # Conversation Flow
    # -----------------------------
    SLEEP_WORDS = _getenv_list("SLEEP_WORDS", "sleep,standby,go to sleep")
    EXIT_WORDS = _getenv_list("EXIT_WORDS", "quit,exit,stop")
    CONTEXT_TURNS = int(os.getenv("CONTEXT_TURNS", "10"))

    # -----------------------------
    # Empathy / Personality
    # -----------------------------
    _cwd = os.getcwd()
    _default_empathy = os.path.join(_cwd, "empathy.json")
    _parent_empathy = os.path.join(os.path.dirname(_cwd), "empathy.json")
    EMPATHY_PATH = os.getenv(
        "EMPATHY_PATH",
        _default_empathy if os.path.exists(_default_empathy) else _parent_empathy
    ).strip()

    # -----------------------------
    # Filler Responses
    # -----------------------------
    FILLER_LATENCY_GATE_S = float(os.getenv("FILLER_LATENCY_GATE_S", "1.2"))
    FILLER_COOLDOWN_S = float(os.getenv("FILLER_COOLDOWN_S", "30"))

    # -----------------------------
    # 🔥 Firestore Toggle
    # -----------------------------
    FIRESTORE_ENABLED = os.getenv("FIRESTORE_ENABLED", "0").strip().lower() in ("1", "true", "yes")

cfg = Config()
