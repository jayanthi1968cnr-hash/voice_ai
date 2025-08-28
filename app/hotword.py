# app/hotword.py
import re
import json
import unicodedata
import difflib
import os
from typing import Tuple, List, Optional

from config import cfg

_alias_db = {}
_hotword_aliases: List[str] = []


# ----------------------------
# Normalization helpers
# ----------------------------
def _clean_keep_space(t: str) -> str:
    t = (t or "").lower()
    t = "".join(c for c in unicodedata.normalize("NFD", t)
                if unicodedata.category(c) != "Mn")
    t = re.sub(r"[^a-z0-9\s]+", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t

def _clean(t: str) -> str:
    t = (t or "").lower()
    t = "".join(c for c in unicodedata.normalize("NFD", t)
                if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]+", "", t)


# ----------------------------
# Alias DB I/O
# ----------------------------
def _alias_key() -> str:
    return _clean_keep_space(cfg.HOTWORD)

def _load_alias_db():
    global _alias_db, _hotword_aliases
    try:
        if os.path.exists(cfg.HOTWORD_ALIASES_PATH):
            with open(cfg.HOTWORD_ALIASES_PATH, "r", encoding="utf-8") as f:
                _alias_db = json.load(f)
        else:
            _alias_db = {}
    except Exception:
        _alias_db = {}
    _hotword_aliases[:] = list(dict.fromkeys(_alias_db.get(_alias_key(), [])))

def _save_alias_db():
    try:
        os.makedirs(os.path.dirname(cfg.HOTWORD_ALIASES_PATH) or ".", exist_ok=True)
        _alias_db[_alias_key()] = _hotword_aliases[:]
        with open(cfg.HOTWORD_ALIASES_PATH, "w", encoding="utf-8") as f:
            json.dump(_alias_db, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


# ----------------------------
# Seeding from presets + env
# ----------------------------
def _seed_accent_variants_multi(word: str, presets_csv: str) -> List[str]:
    presets = [p.strip().lower() for p in (presets_csv or "").split(",") if p.strip()]
    w = _clean_keep_space(word)
    seeds = set()
    if not w:
        return []

    # base + trivial
    seeds.add(w)
    seeds.add(w.replace(" ", "-"))
    seeds.add(w.replace(" ", "' "))
    if len(w) > 3:
        seeds.add(w[:-1])
    # light vowel tweaks
    seeds.add(w.replace("a", "ah"))
    seeds.add(w.replace("o", "aw"))

    # Irish cues
    if "irish" in presets:
        if w.startswith("i"):
            seeds.add("ee" + w[1:])
            seeds.add("ih" + w[1:])
            seeds.add("ee-" + w[1:])
        seeds.add(w.replace("v", "vv"))
        seeds.add(w.replace("va", "vanna"))

    # Indian cues
    if "indian" in presets or "english-india" in presets:
        seeds.add(w.replace("v", "w"))
        seeds.add(w.replace("va", "wa"))
        seeds.add(w.replace("van", "vuh-n"))
        seeds.add(w.replace("van", "wa-n"))
        seeds.add(w.replace("ana", "aana"))
        if w.startswith("i"):
            seeds.add("ee" + w[1:])
            seeds.add("y" + w)

    # include both new & legacy env seed lists
    for s in (cfg.ALL_SEED_ALIASES or []):
        if s:
            seeds.add(_clean_keep_space(s))

    seeds = [s for s in map(_clean_keep_space, seeds) if s]
    return list(dict.fromkeys(seeds))[:4096]  # generous cap


def _apply_caps():
    if cfg.HOTWORD_MAX_ALIASES <= 0:
        if len(_hotword_aliases) > cfg.HOTWORD_ALIAS_HARD_CAP:
            del _hotword_aliases[:-cfg.HOTWORD_ALIAS_HARD_CAP]
    else:
        if len(_hotword_aliases) > cfg.HOTWORD_MAX_ALIASES:
            del _hotword_aliases[:-cfg.HOTWORD_MAX_ALIASES]


# ----------------------------
# Public: init + matching
# ----------------------------
def init_hotword() -> int:
    """
    Load DB, then ALWAYS merge seeds from presets + .env (ALIASES and HOTWORD_SEED_ALIASES).
    This guarantees your full alias list is used even if the DB already existed.
    """
    _load_alias_db()
    before = len(_hotword_aliases)

    seeds = _seed_accent_variants_multi(cfg.HOTWORD, cfg.ACCENT_PRESET)
    added = 0
    for s in seeds:
        if s not in _hotword_aliases:
            _hotword_aliases.append(s)
            added += 1

    if added:
        _apply_caps()
        _save_alias_db()

    return len(_hotword_aliases)


def is_hotword_hit(text: str, thresh: Optional[float] = None) -> Tuple[bool, Optional[str], list]:
    """
    Return (hit, matched_alias, scored_tokens).
    1) Exact match against known aliases (fast path)
    2) Fuzzy compare if nothing in the alias list matches
    """
    if thresh is None:
        thresh = float(getattr(cfg, "HOTWORD_FUZZY_THRESH", 0.74))

    text_c = _clean_keep_space(text)

    # Exact pass on known aliases
    for alias in _hotword_aliases:
        if _clean(alias) in _clean(text_c):
            return True, alias, []

    # Fuzzy compare
    toks = _tokenize_for_hw(text_c)
    scored = [(tok, _sim(tok, cfg.HOTWORD)) for tok in toks if tok]
    scored.sort(key=lambda x: x[1], reverse=True)
    if scored and scored[0][1] >= thresh:
        alias = _clean_keep_space(scored[0][0])
        if alias and alias not in _hotword_aliases:
            _hotword_aliases.append(alias)
            _apply_caps()
            _save_alias_db()
        return True, alias, scored
    return False, None, scored


def strip_hotword_alias(text: str, alias: Optional[str]) -> str:
    if not text:
        return text
    target = (alias or cfg.HOTWORD).strip()
    pattern = re.compile(rf"\b{re.escape(target)}\b", flags=re.IGNORECASE)
    out = pattern.sub("", text).strip()
    if out != text:
        return out
    ct = _clean_keep_space(text)
    ca = _clean_keep_space(target)
    if ct.startswith(ca + " "):
        return text[len(target):].strip()
    return text


# ----------------------------
# Matching helpers
# ----------------------------
def _levenshtein(a: str, b: str) -> int:
    if a == b: return 0
    if not a: return len(b)
    if not b: return len(a)
    m, n = len(a), len(b)
    dp = list(range(n + 1))
    for i in range(1, m + 1):
        prev, dp[0] = dp[0], i
        for j in range(1, n + 1):
            cur = dp[j]
            cost = 0 if a[i-1] == b[j-1] else 1
            dp[j] = min(dp[j] + 1, dp[j-1] + 1, prev + cost)
            prev = cur
    return dp[n]

def _sim(a: str, b: str) -> float:
    a, b = _clean(a), _clean(b)
    if not a or not b: return 0.0
    lev = 1.0 - (_levenshtein(a, b) / max(len(a), len(b)))
    jw  = difflib.SequenceMatcher(None, a, b).ratio()
    return 0.5 * lev + 0.5 * jw

def _tokenize_for_hw(text: str) -> List[str]:
    hw_words = _clean_keep_space(cfg.HOTWORD).split()
    n = max(1, len(hw_words))
    toks = _clean_keep_space(text).split()
    out = toks[:]
    if n > 1 and len(toks) >= n:
        out += [" ".join(toks[i:i+n]) for i in range(0, len(toks)-n+1)]
    return list(dict.fromkeys(out))  # unique, keep order
