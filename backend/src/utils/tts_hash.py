import hashlib
import re
import unicodedata

_WHITESPACE_RE = re.compile(r"\s+")


def normalize_tts_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text)
    normalized = _WHITESPACE_RE.sub(" ", normalized).strip()
    return normalized


def tts_text_hash(text: str) -> str:
    normalized = normalize_tts_text(text)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()
