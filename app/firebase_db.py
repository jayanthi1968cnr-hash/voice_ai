import os
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime

# === Firebase Init ===
try:
    key_path = os.getenv("FIREBASE_KEY_PATH", "firebase-key.json")
    cred = credentials.Certificate(key_path)
    firebase_admin.initialize_app(cred)
    db = firestore.client()
    print(f"✅ Firebase initialized from {key_path}")
except Exception as e:
    print(f"❌ Firebase init failed: {e}")
    db = None

COLL = "users"
DOC = "shiva"  # You can later make this dynamic


# ------------------------
# Helpers / Safe utilities
# ------------------------
def _now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

def _safe_key(key: str) -> str:
    """
    Firestore map field keys must not contain dots.
    Normalize: lowercase, replace non-alnum with underscore.
    """
    key = (key or "").strip().lower()
    out = []
    for ch in key:
        out.append(ch if ch.isalnum() else "_")
    # collapse multiple underscores
    safe = "_".join([p for p in "".join(out).split("_") if p])
    return safe or "key"

def _get_doc_dict() -> dict:
    if not db:
        return {}
    snap = db.collection(COLL).document(DOC).get()
    return snap.to_dict() or {}

def _update(path: dict):
    if not db:
        return
    db.collection(COLL).document(DOC).set(path, merge=True)


# ========================
# Ensure user doc exists
# ========================
def ensure_user_doc():
    if not db:
        return
    doc_ref = db.collection(COLL).document(DOC)
    if not doc_ref.get().exists:
        doc_ref.set({
            "facts": {},
            "reminders": [],
            "events": [],
            "mood_log": [],
            "feedback": [],
            "meta": {
                "created_at": _now_iso(),
                "last_seen": _now_iso(),
                "timezone": "Asia/Kolkata",
            },
        })
        print("🆕 User document created.")
    else:
        print("✅ User document already exists.")


# === 🔐 Facts ===
def save_fact(key: str, value: str):
    if not db:
        return
    safe = _safe_key(key)
    _update({"facts": {safe: value}})

def load_facts() -> dict:
    data = _get_doc_dict()
    return data.get("facts", {})

def delete_fact(key: str):
    if not db:
        return
    safe = _safe_key(key)
    db.collection(COLL).document(DOC).update({f"facts.{safe}": firestore.DELETE_FIELD})


# === ⏰ Reminders ===
def add_reminder(text: str, time_str: str):
    """Store reminders as array of objects (simple, matches your current schema)."""
    if not db:
        return
    item = {
        "message": (text or "").strip(),
        "time": (time_str or "").strip(),
        "created_at": _now_iso(),
        "done": False,
    }
    db.collection(COLL).document(DOC).update({
        "reminders": firestore.ArrayUnion([item])
    })

def get_reminders() -> list:
    data = _get_doc_dict()
    return data.get("reminders", [])

def delete_reminder_by_text(message_or_substring: str):
    """
    Remove reminders whose 'message' contains the given substring (case-insensitive).
    (ArrayUnion/ArrayRemove can't do partial matching; do a read-modify-write.)
    """
    if not db:
        return
    sub = (message_or_substring or "").strip().lower()
    current = get_reminders()
    if not sub:
        return
    kept = [r for r in current if sub not in (r.get("message", "").lower())]
    db.collection(COLL).document(DOC).update({"reminders": kept})


# === 📅 Events ===
def add_event(title: str, date: str, emotion: str = ""):
    if not db:
        return
    item = {
        "title": (title or "").strip(),
        "date": (date or "").strip(),
        "emotion": (emotion or "").strip(),
        "created_at": _now_iso(),
    }
    db.collection(COLL).document(DOC).update({
        "events": firestore.ArrayUnion([item])
    })

def get_events() -> list:
    data = _get_doc_dict()
    return data.get("events", [])

def delete_event_by_title(title: str):
    if not db:
        return
    sub = (title or "").strip().lower()
    current = get_events()
    kept = [e for e in current if sub != e.get("title", "").lower()]
    db.collection(COLL).document(DOC).update({"events": kept})


# === 😄 Mood Log ===
def log_mood(mood: str, note: str, timestamp: str):
    if not db:
        return
    item = {
        "mood": (mood or "").strip(),
        "note": (note or "").strip(),
        "timestamp": (timestamp or "").strip(),
        "created_at": _now_iso(),
    }
    db.collection(COLL).document(DOC).update({
        "mood_log": firestore.ArrayUnion([item])
    })

def get_moods() -> list:
    data = _get_doc_dict()
    return data.get("mood_log", [])

def delete_mood_by_note(note: str):
    if not db:
        return
    sub = (note or "").strip().lower()
    current = get_moods()
    kept = [m for m in current if sub != m.get("note", "").lower()]
    db.collection(COLL).document(DOC).update({"mood_log": kept})


# === 🧠 Meta: Timestamps & Timezone ===
def update_last_seen():
    _update({"meta": {"last_seen": _now_iso()}})

def get_last_seen() -> str | None:
    return (_get_doc_dict().get("meta") or {}).get("last_seen")

def update_timezone(tz: str):
    _update({"meta": {"timezone": (tz or "Asia/Kolkata").strip()}})

def get_timezone() -> str:
    return (_get_doc_dict().get("meta") or {}).get("timezone", "Asia/Kolkata")


# === 🧪 Feedback ===
def log_feedback(message: str, response: str, helpful: bool):
    if not db:
        return
    item = {
        "message": (message or "").strip(),
        "response": (response or "").strip(),
        "was_helpful": bool(helpful),
        "timestamp": _now_iso(),
    }
    db.collection(COLL).document(DOC).update({
        "feedback": firestore.ArrayUnion([item])
    })

def get_feedback() -> list:
    data = _get_doc_dict()
    return data.get("feedback", [])

def delete_feedback_by_message(msg: str):
    if not db:
        return
    sub = (msg or "").strip().lower()
    current = get_feedback()
    kept = [f for f in current if sub != f.get("message", "").lower()]
    db.collection(COLL).document(DOC).update({"feedback": kept})


# === 🔐 Voice Confirmation ===
CONFIRM_DELETE_PHRASE = "confirm delete"

def confirm_delete(voice_input: str) -> bool:
    """
    Keep your original phrase, but also accept common variations.
    """
    t = (voice_input or "").lower()
    return (
        CONFIRM_DELETE_PHRASE in t
        or ("confirm" in t and "delete" in t)
        or ("yes" in t and "delete" in t)
        or ("remove" in t and "yes" in t)
    )


# === Auto-Call Setup ===
if db:
    ensure_user_doc()
# --- Assistant name (store under meta) ---
def set_assistant_name(name: str):
    db.collection(COLL).document(DOC).set(
        {"meta": {"assistant_name": name}}, merge=True
    )

def get_assistant_name() -> str | None:
    doc = db.collection(COLL).document(DOC).get()
    return (doc.to_dict() or {}).get("meta", {}).get("assistant_name")
