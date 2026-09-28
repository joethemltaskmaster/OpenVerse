"""
detector.py

Top-level entry point. Wire this into your Whisper pipeline:

    from detector import ScriptureDetector

    detector = ScriptureDetector()
    refs = detector.detect(whisper_result["text"])

For timestamps (jump straight to the moment a verse was cited), pass the
Whisper segments to `detect_segments` — it treats them as one continuous
text, so references split across segment boundaries still match:

    refs = ScriptureDetector().detect_segments(whisper_result["segments"])
"""

from bisect import bisect_right
from typing import List, Optional

from normalizer import normalize_transcript
from parser import ReferenceParser
from models import ScriptureReference


class ScriptureDetector:
    def __init__(self):
        self._parser = ReferenceParser()

    def detect(self, raw_text: str, timestamp: Optional[float] = None) -> List[ScriptureReference]:
        clean_text = normalize_transcript(raw_text)
        return self._parser.parse(clean_text, timestamp=timestamp)

    def detect_segments(self, segments) -> List[ScriptureReference]:
        """Detect across Whisper segments as ONE continuous text so a
        reference split over a segment boundary ("Romans chapter" /
        "8 verse 28") is still matched. Each reference's timestamp is the
        start time of the segment where the reference begins."""
        parts, starts, times, pos = [], [], [], 0
        for seg in segments:
            text = normalize_transcript(seg["text"])
            if not text:
                continue
            starts.append(pos)
            times.append(seg["start"])
            parts.append(text)
            pos += len(text) + 1  # +1 for the joining space

        refs = self._parser.parse(" ".join(parts))
        for r in refs:
            r.timestamp = times[bisect_right(starts, r.start_char) - 1]
        return refs


if __name__ == "__main__":
    sample_transcript = """
    Turn with me to 2 John chapter 1 verse 3 to 8. This is such a
    beautiful passage. Now if you look at first Corinthians chapter
    thirteen verse four, Paul tells us love is patient. Let's also read
    John 3:16. And back in 2 John, now look at verse 5 again — what a
    powerful truth. Finally, Habakuk chapter two verse four reminds us
    that the just shall live by faith.
    """

    detector = ScriptureDetector()
    references = detector.detect(sample_transcript)

    for ref in references:
        tag = " (inferred)" if ref.inferred_from_context else ""
        print(f"{ref}{tag}  <-  '{ref.raw_text}'")
