import json

def extract_first_json(s: str) -> dict:
    start = s.find('{'); end = s.rfind('}')
    if start == -1 or end == -1 or end <= start: return {}
    try:
        return json.loads(s[start:end+1])
    except Exception:
        return {}
