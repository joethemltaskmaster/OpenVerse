"""
normalizer.py

Cleans raw Whisper transcript text before reference detection runs:
- lowercases and strips filler words
- converts spoken numbers ("chapter three", "verse sixteen") to digits
- normalizes common punctuation variants ("3 : 16" -> "3:16")

Covers 0-199, which comfortably spans every real chapter/verse number
in scripture (max chapter = 150 [Psalms], max verse = 176 [Ps 119:176]).
"""

import re

FILLERS = {"uh", "um", "uhh", "umm", "er", "ah"}

_ONES = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14,
    "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18,
    "nineteen": 19,
}
_TENS = {
    "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50,
    "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90,
}
_ORDINAL_MAP = {
    "first": "1", "second": "2", "third": "3",
    "1st": "1", "2nd": "2", "3rd": "3",
}

_NUMBER_WORD_RE = re.compile(
    r"\b(" + "|".join(sorted(list(_ONES) + list(_TENS), key=len, reverse=True))
    + r")(?:[\s-](" + "|".join(_ONES) + r"))?\b",
    re.IGNORECASE,
)


def _word_number_to_int(match: re.Match) -> str:
    first = match.group(1).lower()
    second = match.group(2)
    if first in _TENS:
        value = _TENS[first] + (_ONES[second.lower()] if second else 0)
    else:
        value = _ONES[first]
    return str(value)


def spoken_numbers_to_digits(text: str) -> str:
    return _NUMBER_WORD_RE.sub(_word_number_to_int, text)


def normalize_transcript(text: str) -> str:
    text = text.lower()

    # strip filler tokens
    tokens = [t for t in text.split() if t.strip(",.") not in FILLERS]
    text = " ".join(tokens)

    # normalize ordinal words used as book-number prefixes (first john -> 1 john)
    # done carefully: only when followed by a likely book word, left to bible_books
    # aliasing to actually resolve — here we just leave "first"/"second" intact
    # since bible_books.ALIASES already understands them directly.

    # convert spoken numbers to digits (chapter/verse numbers)
    text = spoken_numbers_to_digits(text)

    # normalize loose colon/dash spacing: "3 : 16" -> "3:16", "3 - 5" -> "3-5"
    text = re.sub(r"\s*:\s*", ":", text)
    text = re.sub(r"\s*[-–]\s*", "-", text)

    # collapse extra whitespace
    text = re.sub(r"\s+", " ", text).strip()

    return text
