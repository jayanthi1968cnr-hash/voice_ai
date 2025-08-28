from __future__ import annotations
from typing import List, Dict
from datetime import datetime

try:
    from firebase_db import db, COLL, DOC
except Exception:
    db, COLL, DOC = None, "users", "shiva"

def write_summary(text: str):
    if not db: return
    ref = db.collection(COLL).document(DOC).collection("sessions").document("default")
    ref.set({"summary": text, "updated_at": datetime.now().isoformat()}, merge=True)

def read_summary() -> str:
    if not db: return ""
    ref = db.collection(COLL).document(DOC).collection("sessions").document("default").get()
    return (ref.to_dict() or {}).get("summary", "")
