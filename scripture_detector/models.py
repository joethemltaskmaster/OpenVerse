from dataclasses import dataclass
from typing import Optional


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
