# 🧠 Voice AI Assistant

A personal ChatGPT-like voice assistant built in Python, with hotword detection, real-time voice transcription, LLM response generation, text-to-speech, and Firestore-based long-term memory.

---

## 📦 Features

- 🎙️ Hotword-based activation (`Ivana`)
- 🎧 Fast STT using `faster-whisper`
- 🧠 Natural replies via Groq API (LLM)
- 🔊 Responsive TTS with interrupt (`playsound`)
- 🧠 Firestore integration for:
  - Memory (facts, reminders)
  - Deletion by voice
- 🎛️ Global mic mute during TTS playback to avoid echo/trigger loops
- 🧩 Fully modular state-driven architecture: `IDLE → LISTENING → PROCESSING → SPEAKING`
- 🌐 Future plugin system ready

---

## 🗂️ Project Structure

