"""
version_lookup.py

VersionLookup — resolves a scripture reference into actual Bible text,
using a locally bundled KJV dataset (kjv.json, sourced and validated
against bible_books.CHAPTER_COUNTS: 66/66 books, 31,102 verses).

Responsibility boundary: this module ONLY retrieves text. It knows
nothing about screen presentation, timing, or VerseEvents — that is
VersePresenter's job (see verse_presenter.py). It also does not define
or duplicate book-name canonicalization: it trusts whatever canonical
name it's given and validates against bible_books.py's registry, the
single source of truth for book names shared with the detector.
"""

import json
import os
from typing import List, Optional, Tuple

from scripture_detector.bible_books import CHAPTER_COUNTS

_DEFAULT_DATA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "kjv.json")


class VerseNotFoundError(KeyError):
    pass


class VersionLookup:
    """Loads the dataset once; indexed book -> chapter -> verse -> text."""

    def __init__(self, data_path: str = _DEFAULT_DATA_PATH, version: str = "kjv"):
        self.version = version
        with open(data_path, encoding="utf-8") as f:
            self._data = json.load(f)
        self._validate_against_registry()

    def _validate_against_registry(self):
        """Fail loudly at load time, not at some random lookup later, if this
        dataset and bible_books.py ever drift apart (e.g. someone edits one
        without the other)."""
        missing = set(CHAPTER_COUNTS) - set(self._data)
        if missing:
            raise ValueError(
                f"kjv.json is missing books that bible_books.py defines: {sorted(missing)}"
            )
        for book, expected_chapters in CHAPTER_COUNTS.items():
            actual_chapters = len(self._data[book])
            if actual_chapters != expected_chapters:
                raise ValueError(
                    f"kjv.json has {actual_chapters} chapters for '{book}', "
                    f"bible_books.py expects {expected_chapters}"
                )

    def verse(self, book: str, chapter: int, verse: int) -> str:
        """book must already be a canonical name from bible_books.py
        (e.g. via bible_books.normalize_book_name)."""
        try:
            return self._data[book][str(chapter)][str(verse)]
        except KeyError as e:
            raise VerseNotFoundError(f"{book} {chapter}:{verse} not found in {self.version}") from e

    def verse_range(
        self, book: str, chapter: int, verse_start: int, verse_end: Optional[int] = None
    ) -> List[Tuple[int, str]]:
        """Returns [(verse_number, text), ...] for verse_start..verse_end inclusive."""
        v_end = verse_end if verse_end is not None else verse_start
        return [(v, self.verse(book, chapter, v)) for v in range(verse_start, v_end + 1)]

    def resolve(self, ref) -> List[Tuple[int, str]]:
        """Convenience for the presenter layer: takes anything with
        book/chapter/verse_start/verse_end attributes (a ScriptureReference)
        and returns [(verse_number, text), ...]. Whole-chapter references
        (verse_start is None) resolve every verse in the chapter."""
        if ref.verse_start is None:
            chapter_data = self._data[ref.book][str(ref.chapter)]
            return [(int(v), t) for v, t in sorted(chapter_data.items(), key=lambda kv: int(kv[0]))]
        return self.verse_range(ref.book, ref.chapter, ref.verse_start, ref.verse_end)
