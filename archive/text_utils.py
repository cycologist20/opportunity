# ok_mvp/text_utils.py
import re
from typing import List

def sanitize_filename(name: str, max_len: int = 240) -> str:
    """Sanitize a string so it’s safe as a filename on most filesystems."""
    name = re.sub(r'[\\/*?:"<>|]+', " - ", name).strip()
    name = re.sub(r"\s+", " ", name)
    name = name.strip(" .")
    if len(name) > max_len:
        name = name[:max_len].rstrip()
    return name or "transcript"

def normalize_for_compare(s: str) -> str:
    s = s.lower()
    s = re.sub(r"\[.*?\]|\(.*?\)", "", s)
    s = re.sub(r"[^\w\s']+", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def strip_stage_tags(line: str) -> str:
    line = re.sub(r"(?i)\s*(\[[^\]]+\]|\([^)]+\))\s*", " ", line)
    return re.sub(r"\s+", " ", line).strip()

def dedupe_with_window(lines: List[str], window: int, strip_tags: bool) -> List[str]:
    out: List[str] = []
    recent_norms: List[str] = []
    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        if strip_tags:
            line = strip_stage_tags(line)
            if not line:
                continue
        norm = normalize_for_compare(line)
        if norm and norm not in recent_norms:
            out.append(line)
            recent_norms.append(norm)
            if len(recent_norms) > max(1, window):
                recent_norms.pop(0)
    return out

def finalize_text(lines: List[str], window: int = 3, strip_tags: bool = False) -> str:
    """Common finalizer: dedupe + collapse excess blank lines."""
    lines = dedupe_with_window(lines, window, strip_tags)
    text = "\n".join(lines)
    return re.sub(r"\n{3,}", "\n\n", text).strip()

def vtt_to_text(vtt: str, window: int = 3, strip_tags: bool = False) -> str:
    vtt = re.sub(r"^\ufeff?WEBVTT.*?\n+", "", vtt, flags=re.IGNORECASE | re.DOTALL)
    vtt = re.sub(r"(?m)^NOTE.*?(?:\n\n|\Z)", "", vtt, flags=re.DOTALL)
    vtt = re.sub(r"(?m)^STYLE.*?(?:\n\n|\Z)", "", vtt, flags=re.DOTALL)
    vtt = re.sub(r"\d{2}:\d{2}:\d{2}\.\d{3}\s*-->\s*\d{2}:\d{2}:\d{2}\.\d{3}.*", "", vtt)
    vtt = re.sub(r"(?m)^\d+\s*$", "", vtt)
    vtt = re.sub(r"<[^>]+>", "", vtt)
    lines = [ln.strip() for ln in vtt.splitlines() if ln.strip()]
    return finalize_text(lines, window=window, strip_tags=strip_tags)