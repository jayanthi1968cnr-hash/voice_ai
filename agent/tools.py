# agent/tools.py
from datetime import datetime
from firebase_db import save_fact, add_reminder, get_reminders
from config import cfg

def get_time() -> str:
    """Simple utility: returns the current time in human-readable format."""
    now = datetime.now()
    return f"The time is {now.strftime('%I:%M %p')}."

def save_fact_tool(args: dict) -> str:
    """Save a user fact to memory."""
    k = args.get("key") or args.get("name")
    v = args.get("value") or args.get("content")
    if not k or not v:
        return "Sorry, I need both a key and value to save a fact."
    save_fact(k, v)
    return f"Got it. I'll remember that {k} is {v}."

def add_reminder_tool(args: dict) -> str:
    """Add a reminder with optional timestamp."""
    what = args.get("what") or args.get("reminder")
    when = args.get("when_iso")
    if not what:
        return "What should I remind you about?"
    add_reminder(what, when)
    if when:
        return f"Okay, I’ve set a reminder for: {what} at {when}."
    return f"Reminder added: {what}."

def set_assistant_name(args: dict) -> str:
    name = args.get("name") or args.get("assistant_name")
    if not name:
        return "Please tell me what you'd like to call me."
    cfg.HOTWORD = name.strip()
    return f"Thanks! You can now call me {name}."

# Tool dispatch map
TOOL_FUNCTIONS = {
    "get_time": get_time,
    "save_fact": save_fact_tool,
    "add_reminder": add_reminder_tool,
    "set_assistant_name": set_assistant_name,
}
