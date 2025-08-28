# app/intent.py
import re, os, json, random
from typing import Dict, List
from config import cfg

# -----------------------------
# Intent labels
# -----------------------------
INT_GREETING  = "greeting"
INT_CHITCHAT  = "chitchat"
INT_TASK      = "task"
INT_COMPLEX   = "complex"
INT_HAPPY     = "happy"
INT_EMO_TIRE  = "emo_tired"
INT_EMO_SAD   = "emo_sad"
INT_EMO_ANGR  = "emo_anger"
INT_EMO_STRS  = "emo_stress"
INT_EMO_PAIN  = "emo_pain"

# -----------------------------
# Regex patterns
# -----------------------------
GREETING_PAT = re.compile(
    r"\b(hi|hello|hey|good\s*(morning|afternoon|evening))\b|"
    r"\b(how\s*are\s*you|how're\s*you)\b", re.I
)

HAPPY_PAT = re.compile(
    r"\b(happy|great|awesome|amazing|fantastic|wonderful|glad|excited|excellent|nice|love(d)?)\b", re.I
)

TIRED_PAT = re.compile(
    r"\b(tired|exhausted|sleepy|drained|fatigued|worn\s*out|wiped|shattered)\b", re.I
)

SAD_PAT = re.compile(
    r"\b(sad|lonely|depressed|down|blue|heartbroken|upset|hurt|unhappy)\b", re.I
)

ANGER_PAT = re.compile(
    r"\b(angry|mad|furious|annoyed|irritated|frustrated|pissed)\b", re.I
)

STRESS_PAT = re.compile(
    r"\b(stressed|overwhelmed|burn(ed)?\s*out|under\s*pressure|anxious|anxiety|panic)\b", re.I
)

PAIN_PAT = re.compile(
    r"\b(sick|ill|pain|hurts?|ache|fever|cold|flu|migraine|headache|nausea|vomit)\b", re.I
)

# "Complex" intent keywords (how/why/tutorial/guide/steps/explain)
COMPLEX_PAT = re.compile(
    r"\b(how|why|tutorial|guide|walk\s*me\s*through|steps|explain|configure|"
    r"set\s*up|troubleshoot|compare|best\s*way|pros\s*and\s*cons|design|"
    r"architecture|algorithm|calculate|derive|implement)\b", re.I
)

# "Simple" task patterns (short facts); we still treat as task unless complex is hit
SIMPLE_PAT = re.compile(
    r"\b(what\s*is|where\s*is|who\s*is|define|meaning\s*of|price\s*of|time\s*in)\b", re.I
)

# -----------------------------
# Empathy defaults (from your lists)
# -----------------------------
DEFAULT_EMPATHY: Dict[str, List[str]] = {
    "tired": [
        "I'm sorry to hear that. I hope you can get some rest soon.",
        "That sounds exhausting. Please take a break if you need one.",
        "It's okay to feel that way. You've been working so hard.",
        "I understand. I hope you can find some time to recharge.",
        "That sounds draining. Maybe a short pause would help?",
        "Take it easy. You've been putting in a lot of effort.",
        "It's completely normal to feel tired. Be kind to yourself.",
        "I'm sorry you're feeling that. Try to take a moment for yourself.",
        "That sounds like a lot. Remember to prioritize your well-being.",
        "I hear you. Don't push yourself too hard.",
        "I'm sorry you're feeling this way. I hope you can get some rest.",
        "That sounds tough. Remember to take a break.",
        "I get it—you’ve been putting in a lot of effort. Be gentle with yourself.",
        "That sounds draining. Want me to help distract you with something lighter?",
        "A little rest can make a big difference. Hope you feel better.",
        "I’m here if you need me, but I hope you get to relax.",
        "I hear how tired you are. Don't forget to take care of yourself.",
        "It’s okay to be tired. The work you're doing is significant.",
        "That sounds like a lot. Remember to step away for a bit.",
        "I hear you, and it sounds like you could use a rest.",
        "That's a lot to handle. Remember to breathe.",
        "I'm sorry you feel so worn out.",
        "I hope things ease up for you soon.",
        "It's important to rest when you're tired.",
        "I hear the exhaustion. Please take a break.",
    ],
    "sad": [
        "I'm sorry you're feeling that way. Is there anything I can help with?",
        "That sounds difficult. I'm here for you if you want to talk.",
        "I hear the sadness in your voice. I'm here to listen.",
        "That's a tough feeling. I hope things start to look up for you.",
        "It's okay to feel sad. Please know that I'm here to support you.",
        "I'm sorry to hear that. I hope your day gets better.",
        "That sounds really tough. Please remember that you're not alone.",
        "I'm sorry. I hope you can find some comfort soon.",
        "I'm here for you, even if it's just to listen.",
        "That sounds heartbreaking. Please take the time you need to heal.",
        "I'm so sorry you feel that way. I'm here to help in any way I can.",
        "That sounds heavy. I'm sending you my support.",
        "I hear you. I hope you can find some joy in your day.",
        "That sounds difficult. I'm here if you need a distraction.",
        "I'm sorry. No one deserves to feel that way.",
        "I hear you. I'm here to listen.",
        "That sounds like a difficult time. My digital shoulder is here for you.",
        "I'm sorry you're going through this.",
        "I hope you can find some comfort.",
        "Please know that your feelings are valid.",
        "It's okay to be sad. There's no rush to feel better.",
        "I hear you. Sometimes it helps just to talk.",
        "I’m here for you. Just let me know what you need.",
        "I’m sorry. I hope things get easier.",
    ],
    "anger": [
        "I understand. I'll try to be more helpful.",
        "I'm sorry. I hope I haven't added to your frustration.",
        "That sounds annoying. I'll do my best to get this right.",
        "I hear your frustration. Let's try to solve this together.",
        "I'm sorry for the inconvenience. What can I do to help?",
        "I get it. That's a very frustrating situation.",
        "I'm sorry for the trouble. Let's start over if you'd like.",
        "I'll try to be more clear. Please let me know what's wrong.",
        "I hear your frustration. What can I do to make this better?",
        "I understand. I'll make sure to correct that.",
        "I apologize. What seems to be the issue?",
        "I understand why you're frustrated. I'll try to improve.",
        "I hear you loud and clear. Let's figure this out.",
        "It sounds like you're feeling pretty annoyed.",
        "I'm sorry. I'm here to help, not to frustrate you.",
        "That sounds really irritating. I apologize.",
        "Let's take a moment. I'll try to do better.",
        "I hear you. What would you like me to do?",
    ],
    "stress": [
        "That sounds like a lot to handle. Remember to take it one step at a time.",
        "It's okay to feel overwhelmed. What's the most important thing right now?",
        "I hear your stress. Maybe we can tackle one task at a time?",
        "Take a deep breath. Let's break this down together.",
        "That sounds like a lot of pressure. I can help simplify things.",
        "I'm sorry you're feeling that way. It's okay to pause and reset.",
        "I understand. I'm here to help lighten your load.",
        "That sounds very stressful. What can I help you with first?",
        "I'm sorry you feel overwhelmed. Let me know if I can help you organize.",
        "It's a lot, but we can manage it.",
        "Don't worry, we'll get through this.",
        "I hear the stress in your voice. What's on your mind?",
        "Take a moment to yourself. I'll be here when you're ready.",
        "I understand. It’s hard to stay on top of everything.",
    ],
    "pain": [
        "I'm sorry you're not feeling well. I hope you get better soon.",
        "I'm sorry you're in pain. Please take it easy.",
        "I hope you can find some relief soon.",
        "I'm sorry to hear that. Do you need me to look something up for you?",
        "Please take care of yourself. I wish you a speedy recovery.",
        "I'm sorry you're feeling poorly. Is there anything I can do?",
    ],
    "general": [
        "Thank you for sharing that with me.",
        "I hear you, and I appreciate you telling me that.",
        "It sounds like you're going through a lot. I'm here to help.",
        "I'm sorry to hear that. Is there anything I can do?",
        "I hear you. I'm here to listen and help as best I can.",
        "That sounds like a lot to deal with. I'm here for you.",
        "I'm sorry you're feeling that way. Your feelings are valid.",
        "It sounds like that was a difficult experience.",
        "Thank you for telling me. That sounds very important.",
        "I hear you. I'm listening.",
        "I can only imagine how that must feel.",
        "That must have been tough.",
        "I hear the emotion in your voice.",
        "I'm here to support you.",
        "I understand. It's not easy.",
        "Thank you for trusting me with that.",
        "I'm here to help.",
        "I'm here to listen.",
        "I hear you. What's on your mind?",
    ],
    "happy": [
        "That's wonderful to hear!",
        "I'm so glad things are going well for you.",
        "That's fantastic!",
        "That's great news.",
        "I'm happy for you.",
        "What's making you so happy?",
        "Tell me more about that!",
        "That's a lovely thing to hear. Keep it up!",
        "That's wonderful. It sounds like you're having a great day.",
        "I'm thrilled to hear that.",
        "Your excitement is contagious!",
        "That's a fantastic achievement.",
        "That's amazing! You deserve to be happy.",
    ],
    "question_processing": [
        "Got it—give me a moment.",
        "Let me check that for you.",
        "Working on it—one sec.",
        "Digging into that now.",
        "On it—pulling the details.",
        "Let me look that up.",
        "Checking the latest for you.",
        "Gathering the steps for you.",
        "One moment, verifying.",
        "Let me make sure I get this right.",
    ],
}

# -----------------------------
# Load empathy JSON if provided
# -----------------------------
_empathy = DEFAULT_EMPATHY
try:
    if cfg.EMPATHY_PATH and os.path.exists(cfg.EMPATHY_PATH):
        with open(cfg.EMPATHY_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                # merge with defaults (JSON can override or add)
                merged = dict(DEFAULT_EMPATHY)
                merged.update({k: v for k, v in data.items() if isinstance(v, list)})
                _empathy = merged
except Exception:
    _empathy = DEFAULT_EMPATHY  # safe fallback


# -----------------------------
# Intent classifier
# -----------------------------
def classify_intent(t: str) -> str:
    tl = (t or "").strip().lower()
    if not tl:
        return INT_CHITCHAT
    if GREETING_PAT.search(tl):
        return INT_GREETING
    if HAPPY_PAT.search(tl):
        return INT_HAPPY
    if TIRED_PAT.search(tl):
        return INT_EMO_TIRE
    if SAD_PAT.search(tl):
        return INT_EMO_SAD
    if ANGER_PAT.search(tl):
        return INT_EMO_ANGR
    if STRESS_PAT.search(tl):
        return INT_EMO_STRS
    if PAIN_PAT.search(tl):
        return INT_EMO_PAIN
    if COMPLEX_PAT.search(tl):
        return INT_COMPLEX
    if SIMPLE_PAT.search(tl) or len(tl.split()) <= 3:
        return INT_TASK
    return INT_TASK


def _pick(lines: List[str]) -> str:
    return random.choice(lines) if lines else ""


def maybe_empathy_reply(text: str, intent: str) -> str | None:
    cat = None
    if intent == INT_EMO_TIRE:  cat = "tired"
    elif intent == INT_EMO_SAD: cat = "sad"
    elif intent == INT_EMO_ANGR: cat = "anger"
    elif intent == INT_EMO_STRS: cat = "stress"
    elif intent == INT_EMO_PAIN: cat = "pain"
    elif intent == INT_HAPPY:    cat = "happy"
    if cat:
        return _pick(_empathy.get(cat, []) or _empathy.get("general", []))
    return None


def maybe_greeting_reply(text: str) -> str | None:
    t = (text or "").lower().strip()
    if re.search(r"\bhow\s*are\s*you\b", t):
        return "I’m steady and focused. What should we tackle first?"
    if re.search(r"\b(hi|hello|hey)\b", t):
        return "Hey! What can I do for you right now?"
    m = re.search(r"\bgood\s*(morning|afternoon|evening)\b", t)
    if m:
        part = m.group(1)
        return f"Good {part}! What’s on your list?"
    return None


def processing_lines() -> List[str]:
    return _empathy.get("question_processing", DEFAULT_EMPATHY["question_processing"])[:]
