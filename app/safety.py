import re

def moderate(text: str) -> tuple[bool, str]:
    banned = ["how to make a bomb", "child sexual"]
    for b in banned:
        if b in text.lower():
            return False, "I cant help with that."
    return True, text

def redact_pii(text: str) -> str:
    text = re.sub(r"[\w.+-]+@[\w-]+\.[\w.-]+", "[email]", text)
    text = re.sub(r"\b\+?\d[\d\s()-]{7,}\b", "[phone]", text)
    return text
