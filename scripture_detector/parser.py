"""
parser.py  (v2 — fixes two bugs found during smoke-testing)

Bug 1: the book-name capture group was unbounded and greedily swallowed
a preceding filler word ("read john 3:16" matched book="read john",
which failed to resolve and silently dropped the whole reference).
Fixed by requiring each captured token to NOT be a common filler word
(STOPWORDS), via a per-token negative lookahead, and by trying the
longest captured phrase first when resolving against the book registry
(so "first john" is preferred over just "john").

Bug 2: verse-only follow-ups ("verse 5") were resolved in a separate
pass AFTER all full references had already been scanned, so they always
inherited the LAST book/chapter in the whole transcript instead of the
nearest PRECEDING one. Fixed by merging all candidate matches into a
single position-ordered stream and resolving them in one left-to-right
pass, updating parser state incrementally as we go.
"""

import re
from typing import List, Optional

from bible_books import normalize_book_name, is_valid_chapter
from models import ScriptureReference

STOPWORDS = {
    "to", "at", "in", "from", "read", "turn", "turning", "open", "opening",
    "look", "looking", "lets", "let", "us", "also", "and", "now", "back",
    "up", "into", "unto", "please", "everyone", "okay", "ok", "this",
    "that", "again", "see", "go", "going", "today", "with", "me", "we",
    "you", "your", "our", "the", "a", "an", "is", "was", "were", "if",
    "so", "here", "over",
}
_STOPWORD_ALT = "|".join(sorted(STOPWORDS, key=len, reverse=True))
# \b anchors each token to a real word start — without it, a bare
# negative lookahead lets the regex engine start mid-word (e.g. matching
# just the "o" inside "to"), which silently corrupted match boundaries.
_TOKEN = rf"\b(?!(?:{_STOPWORD_ALT})\b)[a-z0-9]+"
# 1 to 3 whitespace-separated tokens, none of which is a filler word
_BOOK_CAPTURE = rf"(?:{_TOKEN}\s+){{0,2}}{_TOKEN}"

FULL_REF_RE = re.compile(
    rf"""
    (?P<book>{_BOOK_CAPTURE})\s+
    chapter\s+(?P<chapter>\d{{1,3}})
    (?:
        \s*[,:]?\s*
        verse[s]?\s+(?P<verse_start>\d{{1,3}})
        (?:\s*(?:to|through|-|–)\s*(?P<verse_end>\d{{1,3}}))?
    )?
    """,
    re.IGNORECASE | re.VERBOSE,
)

COLON_REF_RE = re.compile(
    rf"""
    (?P<book>{_BOOK_CAPTURE})\s+
    (?P<chapter>\d{{1,3}}):(?P<verse_start>\d{{1,3}})
    (?:-(?P<verse_end>\d{{1,3}}))?
    """,
    re.IGNORECASE | re.VERBOSE,
)

VERSE_ONLY_RE = re.compile(
    r"verse[s]?\s+(?P<verse_start>\d{1,3})"
    r"(?:\s*(?:to|through|-|–)\s*(?P<verse_end>\d{1,3}))?",
    re.IGNORECASE,
)


def _resolve_book_phrase(captured: str) -> Optional[str]:
    """Try the full captured phrase first, then progressively drop the
    leftmost token. Prefers 'first john' -> '1 john' over accidentally
    matching just the trailing word 'john'."""
    words = captured.split()
    for drop in range(len(words)):
        candidate = " ".join(words[drop:])
        canonical = normalize_book_name(candidate)
        if canonical:
            return canonical
    return None


class ReferenceParser:
    """Stateful parser: remembers the last resolved book/chapter so a
    trailing verse-only mention ('verse 5') resolves against whichever
    reference most recently preceded it in the transcript."""

    def __init__(self):
        self.current_book: Optional[str] = None
        self.current_chapter: Optional[int] = None

    def parse(self, text: str, timestamp: Optional[float] = None) -> List[ScriptureReference]:
        candidates = []  # (start, end, kind, match)

        for m in FULL_REF_RE.finditer(text):
            candidates.append((m.start(), m.end(), "full", m))
        for m in COLON_REF_RE.finditer(text):
            candidates.append((m.start(), m.end(), "full", m))
        for m in VERSE_ONLY_RE.finditer(text):
            candidates.append((m.start(), m.end(), "verse_only", m))

        # sort by position; when spans overlap, "full" wins over "verse_only"
        candidates.sort(key=lambda c: (c[0], c[2] != "full"))

        results: List[ScriptureReference] = []
        claimed: List[tuple] = []

        for start, end, kind, m in candidates:
            if any(not (end <= cs or start >= ce) for cs, ce in claimed):
                continue

            if kind == "full":
                ref = self._resolve_full_match(m, timestamp)
            else:
                ref = self._resolve_verse_only(m, timestamp)

            if ref:
                results.append(ref)
                claimed.append((start, end))

        results.sort(key=lambda r: r.start_char)
        return results

    # -- internals ---------------------------------------------------

    def _resolve_full_match(self, m, timestamp) -> Optional[ScriptureReference]:
        canonical_book = _resolve_book_phrase(m.group("book"))
        if not canonical_book:
            return None

        chapter = int(m.group("chapter"))
        if not is_valid_chapter(canonical_book, chapter):
            return None

        verse_start = m.groupdict().get("verse_start")
        verse_end = m.groupdict().get("verse_end")

        self.current_book = canonical_book
        self.current_chapter = chapter

        return ScriptureReference(
            book=canonical_book,
            chapter=chapter,
            verse_start=int(verse_start) if verse_start else None,
            verse_end=int(verse_end) if verse_end else (int(verse_start) if verse_start else None),
            raw_text=m.group(0),
            start_char=m.start(),
            end_char=m.end(),
            timestamp=timestamp,
        )

    def _resolve_verse_only(self, m, timestamp) -> Optional[ScriptureReference]:
        if not self.current_book or not self.current_chapter:
            return None  # no prior context to inherit from

        verse_start = int(m.group("verse_start"))
        verse_end_raw = m.group("verse_end")

        return ScriptureReference(
            book=self.current_book,
            chapter=self.current_chapter,
            verse_start=verse_start,
            verse_end=int(verse_end_raw) if verse_end_raw else verse_start,
            raw_text=m.group(0),
            start_char=m.start(),
            end_char=m.end(),
            timestamp=timestamp,
            inferred_from_context=True,
        )
