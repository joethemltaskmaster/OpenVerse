"""
presentation/verse_splitter.py

Splits oversize VerseEvents into multiple events, preserving timeline.
Additive — VersePresenter.expand() is unchanged.
"""
from __future__ import annotations

import re
from typing import List

from scripture_detector.models import VerseEvent

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?;])\s+")
MIN_WORDS_PER_PIECE = 10


def _estimate_duration(text: str, wpm: int, min_gap: float) -> float:
    return max(len(text.split()) * 60.0 / wpm, min_gap)


def _split_into_pieces(text: str, max_words: int) -> List[str]:
    text = text.strip()
    if not text:
        return []
    sentences = _SENTENCE_SPLIT.split(text)
    pieces, current, current_wc = [], [], 0
    for sentence in sentences:
        wc = len(sentence.split())
        if wc > max_words:
            if current:
                pieces.append(" ".join(current).strip())
                current, current_wc = [], 0
            words = sentence.split()
            for i in range(0, len(words), max_words):
                pieces.append(" ".join(words[i:i + max_words]))
        elif current_wc + wc <= max_words:
            current.append(sentence)
            current_wc += wc
        else:
            pieces.append(" ".join(current).strip())
            current, current_wc = [sentence], wc
    if current:
        pieces.append(" ".join(current).strip())
    if len(pieces) >= 2 and len(pieces[-1].split()) < MIN_WORDS_PER_PIECE:
        pieces[-1] = pieces[-2] + " " + pieces.pop()
    return [p for p in pieces if p]


def split_long_verses(
    events: List[VerseEvent],
    words_per_minute: int = 150,
    min_gap_seconds: float = 2.0,
    max_words_per_event: int = 55,
) -> List[VerseEvent]:
    out: List[VerseEvent] = []
    for event in events:
        if len(event.text.split()) <= max_words_per_event:
            out.append(event)
            continue
        pieces = _split_into_pieces(event.text, max_words_per_event)
        if len(pieces) <= 1:
            out.append(event)
            continue
        clock = event.display_at
        for piece_text in pieces:
            duration = _estimate_duration(piece_text, words_per_minute, min_gap_seconds)
            out.append(VerseEvent(
                book=event.book, chapter=event.chapter, verse=event.verse,
                text=piece_text, display_at=clock,
                timing_source=event.timing_source, source_ref=event.source_ref,
                duration_estimate=duration,
            ))
            clock += duration
    return out