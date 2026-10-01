"""
verse_presenter.py  (v3 — pure sequential presentation clock)

VersePresenter — takes detected ScriptureReferences in speech/detection
order, resolves their text through VersionLookup, and explodes each one
into individually schedulable VerseEvents on ONE continuous presentation
clock.

TIMING MODEL (precisely):

  display_at      = position on the presentation clock, in seconds from 0.
  duration_estimate = how long this verse occupies the clock before the
                      next verse begins.

  first_event.display_at = 0.0
  event[n].display_at    = event[n-1].display_at + event[n-1].duration_estimate

The preacher's / audio's actual timestamps are IGNORED entirely for this
calculation. display_at is not a speech timestamp; it is a position on a
constructed presentation timeline. Every timestamp on the incoming
ScriptureReference is unused by this module.

ORDER IS PRESERVED. Duplicate references are not collapsed or reordered —
if the same scripture appears twice in the detection stream, both
occurrences are kept in their original sequence, each occupying its own
slot on the presentation clock.

READING PACE: 150 WPM by default.
  seconds_per_verse = word_count * 60 / words_per_minute
  (subject to a min_gap_seconds floor so a very short verse still has a
   visible window on screen.)

This module does not maintain Bible text (VersionLookup's job) and does
not touch the screen (the display layer's job). The display layer already
schedules correctly given a well-formed display_at sequence — it needs no
changes here.
"""

from typing import List

from scripture_detector.models import ScriptureReference, VerseEvent
from lookup.version_lookup import VersionLookup


class VersePresenter:
    """
    words_per_minute: reading-pace constant, used to compute each verse's
        duration_estimate on the presentation clock.
    min_gap_seconds: floor on a verse's duration, so a one-word verse
        doesn't get an unrealistically tiny display window.
    """

    def __init__(
        self,
        lookup: VersionLookup,
        words_per_minute: int = 150,
        min_gap_seconds: float = 2.0,
    ):
        self.lookup = lookup
        self.words_per_minute = words_per_minute
        self.min_gap_seconds = min_gap_seconds

    def _estimate_duration(self, text: str) -> float:
        word_count = len(text.split())
        # 150 WPM => 2.5 words/sec => seconds = words * 60 / WPM.
        seconds = word_count * 60.0 / self.words_per_minute
        return max(seconds, self.min_gap_seconds)

    def expand(self, refs: List[ScriptureReference]) -> List[VerseEvent]:
        """
        refs must already be in speech/detection order (as produced by
        ScriptureDetector — sorted by position in the transcript).

        Builds ONE continuous presentation clock:
          - first verse always starts at display_at = 0.0
          - each subsequent verse starts at
              previous.display_at + previous.duration_estimate

        Preacher/audio timestamps on the incoming refs are ignored.
        Duplicate references are preserved in their original order.
        """
        events: List[VerseEvent] = []
        clock = 0.0

        for ref in refs:
            verse_texts = self.lookup.resolve(ref)  # [(verse_num, text), ...]
            for vnum, text in verse_texts:
                duration = self._estimate_duration(text)
                events.append(
                    VerseEvent(
                        book=ref.book,
                        chapter=ref.chapter,
                        verse=vnum,
                        text=text,
                        display_at=clock,
                        timing_source="estimated",
                        source_ref=ref,
                        duration_estimate=duration,
                    )
                )
                clock += duration

        return events