"""
verse_presenter.py

VersePresenter — takes detected ScriptureReferences, resolves their text
through VersionLookup, and explodes each one into individually
schedulable VerseEvents.

GOLDEN RULE: a real timestamp always takes precedence over an estimate,
and estimation is used in exactly one situation — nowhere else.

Two distinct cases reach this module, and they are handled differently:

1. Several SEPARATE ScriptureReference objects (e.g. "verse 1" spoken,
   then later "verse 2" spoken — each its own detector hit with its own
   real Whisper timestamp). Both already have real timing. Nothing is
   estimated; each keeps its own real timestamp untouched.

2. ONE ScriptureReference covering a spoken range (verse_start != verse_end,
   e.g. "verse 1 to 2" said once). There is exactly ONE real timestamp for
   the whole range — it describes verse_start. There is no second real
   moment for verse_end, so its timing is estimated from a reading-pace
   model. This is the ONLY place this module estimates anything.

VersePresenter does not maintain Bible text itself (that's VersionLookup's
job) and does not touch the screen/display layer — it only produces
VerseEvent objects for something else to render.
"""

from typing import List

from scripture_detector.models import ScriptureReference, VerseEvent
from lookup.version_lookup import VersionLookup


class VersePresenter:
    """
    words_per_minute: reading-pace constant, used ONLY to estimate the gap
        before an estimated-timing verse (case 2 above). Configurable
        rather than hardcoded, since sermon reading pace varies.
    min_gap_seconds: floor on an estimated gap, so a one-word verse doesn't
        get an unrealistically tiny (or zero) display window.
    """

    def __init__(self, lookup: VersionLookup, words_per_minute: int = 150, min_gap_seconds: float = 2.0):
        self.lookup = lookup
        self.words_per_minute = words_per_minute
        self.min_gap_seconds = min_gap_seconds

    def expand(self, refs: List[ScriptureReference]) -> List[VerseEvent]:
        """Explode every reference into VerseEvents and return them in
        display order. Each ref is handled independently — this does not
        merge or reorder across references, only within one."""
        events: List[VerseEvent] = []
        for ref in refs:
            events.extend(self._expand_one(ref))
        events.sort(key=lambda e: e.display_at)
        return events

    def _estimate_gap(self, text: str) -> float:
        word_count = len(text.split())
        return max(word_count / self.words_per_minute * 60.0, self.min_gap_seconds)

    def _expand_one(self, ref: ScriptureReference) -> List[VerseEvent]:
        verse_texts = self.lookup.resolve(ref)  # [(verse_num, text), ...], in verse order
        has_real_timestamp = ref.timestamp is not None
        clock = ref.timestamp if has_real_timestamp else 0.0

        out: List[VerseEvent] = []
        for i, (vnum, text) in enumerate(verse_texts):
            if i == 0:
                # ref.timestamp (if present) is the one real moment this
                # reference carries, and it describes verse_start.
                timing_source = "real" if has_real_timestamp else "estimated"
            else:
                # Case 2: no real timestamp exists for verse_start+1 onward
                # within a single spoken range — estimate from the
                # previous verse's reading time.
                timing_source = "estimated"
                clock += self._estimate_gap(out[-1].text)

            out.append(VerseEvent(
                book=ref.book,
                chapter=ref.chapter,
                verse=vnum,
                text=text,
                display_at=clock,
                timing_source=timing_source,
                source_ref=ref,
            ))
        return out
