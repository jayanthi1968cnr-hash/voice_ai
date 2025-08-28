import re

def detect_affect(text: str) -> str:
    t = (text or '').lower()
    if re.search(r'\b(angry|annoyed|frustrated|wtf)\b', t): return 'angry'
    if re.search(r'\b(sad|down|tired|exhausted)\b', t): return 'sad'
    if re.search(r'\b(thanks|great|awesome|nice|cool)\b', t): return 'positive'
    return 'neutral'
