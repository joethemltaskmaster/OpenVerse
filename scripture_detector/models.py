from dataclasses import dataclass
from typing import Optional, Literal


@dataclass
class ScriptureReference:
    book: str
    chapter: int
    verse_start: Optional[int] = None
    verse_end: Optional[int] = None
    raw_text: str = ""
    start_char: int = 0
    end_char: int = 0
    confidence: float = 1.0
    timestamp: Optional[float] = None
    inferred_from_context: bool = False  # True if book/chapter carried over

    def to_dict(self) -> dict:
        return {
            "book": self.book,
            "chapter": self.chapter,
            "verse_start": self.verse_start,
            "verse_end": self.verse_end,
            "raw_text": self.raw_text,
            "confidence": self.confidence,
            "timestamp": self.timestamp,
            "inferred_from_context": self.inferred_from_context,
        }

    def __str__(self) -> str:
        base = f"{self.book} {self.chapter}"
        if self.verse_start is None:
            return base
        if self.verse_end and self.verse_end != self.verse_start:
            return f"{base}:{self.verse_start}-{self.verse_end}"
        return f"{base}:{self.verse_start}"


@dataclass
class VerseEvent:
    """One individually displayable verse, produced by VersePresenter.
    Golden rule this type exists to make visible: timing_source tells you
    whether display_at came from a real Whisper timestamp or was
    estimated from reading pace — never guess, always check this field."""
    book: str
    chapter: int
    verse: int
    text: str
    display_at: float                       # seconds into the transcript
    timing_source: Literal["real", "estimated"]
    source_ref: "ScriptureReference"         # the reference this was expanded from

    @property
    def is_estimated_timing(self) -> bool:
        return self.timing_source == "estimated"

    def __str__(self) -> str:
        return f"{self.book} {self.chapter}:{self.verse} — {self.text}"