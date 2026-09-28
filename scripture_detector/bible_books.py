"""
bible_books.py

Canonical registry of all 66 books, their chapter counts (for bounds
validation), and an alias table that maps every spoken variant a
preacher/ASR engine might produce ("first john", "1st john", "1 john")
to a single canonical book name.

NOTE on accuracy: chapter counts below are standard and reliable.
Per-chapter verse-count bounds are intentionally NOT hardcoded here —
that table has ~1,189 entries and is easy to get subtly wrong by hand.
For strict verse-level validation, wire in the `pythonbible` package
(pip install pythonbible), which ships a maintained verse-count table.
This module gives you working chapter-level validation out of the box
and a clean seam to plug in verse-level validation later.
"""

from difflib import get_close_matches

# --- Canonical chapter counts (Protestant 66-book canon) ---------------
CHAPTER_COUNTS = {
    "genesis": 50, "exodus": 40, "leviticus": 27, "numbers": 36,
    "deuteronomy": 34, "joshua": 24, "judges": 21, "ruth": 4,
    "1 samuel": 31, "2 samuel": 24, "1 kings": 22, "2 kings": 25,
    "1 chronicles": 29, "2 chronicles": 36, "ezra": 10, "nehemiah": 13,
    "esther": 10, "job": 42, "psalms": 150, "proverbs": 31,
    "ecclesiastes": 12, "song of solomon": 8, "isaiah": 66,
    "jeremiah": 52, "lamentations": 5, "ezekiel": 48, "daniel": 12,
    "hosea": 14, "joel": 3, "amos": 9, "obadiah": 1, "jonah": 4,
    "micah": 7, "nahum": 3, "habakkuk": 3, "zephaniah": 3, "haggai": 2,
    "zechariah": 14, "malachi": 4,
    "matthew": 28, "mark": 16, "luke": 24, "john": 21, "acts": 28,
    "romans": 16, "1 corinthians": 16, "2 corinthians": 13,
    "galatians": 6, "ephesians": 6, "philippians": 4, "colossians": 4,
    "1 thessalonians": 5, "2 thessalonians": 3, "1 timothy": 6,
    "2 timothy": 4, "titus": 3, "philemon": 1, "hebrews": 13,
    "james": 5, "1 peter": 5, "2 peter": 3, "1 john": 5, "2 john": 1,
    "3 john": 1, "jude": 1, "revelation": 22,
}

# Books that come in numbered variants (base name only, no number)
MULTI_PART_BASE_NAMES = {
    "samuel", "kings", "chronicles", "corinthians",
    "thessalonians", "timothy", "peter", "john",
}

ORDINAL_WORDS = {
    "1": ["1", "first", "1st", "one"],
    "2": ["2", "second", "2nd", "two"],
    "3": ["3", "third", "3rd", "three"],
}

# A few common spoken/abbreviated aliases beyond the ordinal expansion.
# Extend this dict as you find real misses in your transcripts.
EXTRA_ALIASES = {
    "psalm": "psalms",
    "song of songs": "song of solomon",
    "revelations": "revelation",
    "philippi": "philippians",  # common ASR slip
}


def _build_alias_map():
    aliases = {}
    for canonical in CHAPTER_COUNTS:
        parts = canonical.split()
        if parts[0] in ORDINAL_WORDS and parts[-1] in MULTI_PART_BASE_NAMES:
            num = parts[0]
            base = " ".join(parts[1:])
            for word in ORDINAL_WORDS[num]:
                aliases[f"{word} {base}"] = canonical
        else:
            aliases[canonical] = canonical
    aliases.update(EXTRA_ALIASES)
    return aliases


ALIASES = _build_alias_map()


def normalize_book_name(raw_text: str, fuzzy: bool = True, cutoff: float = 0.82):
    """
    Map a raw spoken/ASR book-name span to its canonical form.
    Returns the canonical name, or None if no confident match is found.
    """
    key = raw_text.strip().lower()
    if key in ALIASES:
        return ALIASES[key]

    if not fuzzy:
        return None

    # Fuzzy fallback for ASR misheard book names (e.g. "habakuk", "philipians")
    match = get_close_matches(key, ALIASES.keys(), n=1, cutoff=cutoff)
    return ALIASES[match[0]] if match else None


def get_max_chapter(canonical_book: str):
    return CHAPTER_COUNTS.get(canonical_book)


def is_valid_chapter(canonical_book: str, chapter: int) -> bool:
    max_ch = get_max_chapter(canonical_book)
    return max_ch is not None and 1 <= chapter <= max_ch
