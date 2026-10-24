"""Normalize whatever transcribe_audio returns into (text, segments_or_none)."""
from __future__ import annotations
from typing import Optional, Tuple


def normalize_transcript_result(result) -> Tuple[str, Optional[list]]:
    if isinstance(result, str):
        return result, None
    if isinstance(result, dict):
        return result.get("text") or "", result.get("segments") or None
    text = getattr(result, "text", None)
    if text is not None:
        return text, getattr(result, "segments", None) or None
    return str(result), None