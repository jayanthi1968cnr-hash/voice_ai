from typing import Callable, Dict, Any

_SKILLS: Dict[str, Callable[[Dict[str, Any]], Dict[str, Any]]] = {}

def register(name: str):
    def deco(fn: Callable[[Dict[str, Any]], Dict[str, Any]]):
        _SKILLS[name] = fn
        return fn
    return deco

def get(name: str):
    return _SKILLS.get(name)

SKILLS = _SKILLS
