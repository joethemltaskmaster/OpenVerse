# Scripture Reference Detector — scaffold

A working first pass at extracting Bible references from Whisper-transcribed
sermon audio. Verified against real edge cases during development (see
"known limitations" below for what's intentionally out of scope for v1).

## Files
- `bible_books.py` — canonical 66-book registry, chapter-count bounds,
  numbered-book aliasing ("first john"/"1st john"/"1 john" → `1 john`),
  fuzzy correction for misheard names (`habakuk` → `habakkuk`).
- `normalizer.py` — lowercases, strips ASR filler ("uh", "um"), converts
  spoken numbers to digits ("chapter three" → "chapter 3").
- `parser.py` — regex-based candidate detection + a stateful resolver that
  carries the last-known book/chapter forward for verse-only follow-ups
  ("verse 5" with no book/chapter attached).
- `models.py` — `ScriptureReference` dataclass (the output record).
- `detector.py` — orchestrator + example usage. Run directly (`python
  detector.py`) to see it work against a sample transcript.

## Quick start
```python
from detector import ScriptureDetector

detector = ScriptureDetector()
refs = detector.detect(whisper_result["text"])
for r in refs:
    print(r, r.to_dict())
```

For a full sermon with Whisper segment timestamps, feed segments through
one at a time so state (and confidence) carries correctly across the
whole transcript, and so each reference keeps a timestamp:
```python
detector = ScriptureDetector()
all_refs = []
for seg in whisper_result["segments"]:
    all_refs.extend(detector.detect(seg["text"], timestamp=seg["start"]))
```

## What it handles
- Numbered books: `1 John` / `first John` / `1st John` — all normalize to
  the same canonical form.
- Full references: `2 John chapter 1 verse 3 to 8`
- Colon shorthand: `Romans 8:28`, `John 3:16-18`
- Verse-only follow-ups that inherit the nearest preceding book/chapter:
  `...now look at verse 5...`
- Chapter-bounds validation (rejects e.g. `Genesis chapter 51` — Genesis
  only has 50 chapters), which filters a good chunk of ASR noise.
- Fuzzy correction for misheard book names within an edit-distance
  threshold (`habakuk` → `habakkuk`).

## Known limitations (by design, for this first pass)
- **Verse-level bounds aren't validated**, only chapter-level. A precise
  per-chapter verse-count table is ~1,189 entries and too easy to get
  subtly wrong by hand — swap in the `pythonbible` package
  (`pip install pythonbible`) for that layer when you're ready to
  tighten validation.
- **Bare book mentions without a chapter** ("back in 2 John, now...")
  don't update parser state — only a *full* reference (with chapter)
  updates what a later "verse N" inherits from. Worth adding if your
  sermons frequently name a book well before citing its chapter.
- **Single-chapter books** (Jude, Obadiah, Philemon, 2 John, 3 John) are
  only matched when a chapter number is explicitly spoken or a colon is
  used — "Jude verse 3" alone isn't yet special-cased to mean "chapter 1".
- STOPWORDS list (words excluded from book-name capture) is a starting
  set — extend it as you find real transcripts where a filler word
  leaks into a match.

## Suggested next steps
1. Run this against a batch of your real Whisper outputs and build a
   small labeled test corpus from the misses — that'll tell you which
   limitation above actually matters for your content.
2. Swap in `pythonbible` for verse-level bounds checking.
3. If disfluent/self-corrected speech ("John — sorry, First John —
   chapter 2") turns out to be common, add a low-confidence-span escalation
   to an LLM verification pass rather than trying to handle it in regex.

## Verse text (VersionLookup + VersePresenter)

`version_lookup.py` bundles a full KJV dataset (`kjv.json`, ~4.3 MB) keyed
by the exact canonical book names in `bible_books.py` — validated at
import time: 66/66 books, chapter counts matching `CHAPTER_COUNTS`
exactly, 31,102 verses total. `VersionLookup` only retrieves text; it
knows nothing about timing or display.

`verse_presenter.py` explodes a `ScriptureReference` into individual
`VerseEvent`s (one per verse) with a `display_at` time. **Golden rule:
a real timestamp always wins.** Concretely:
- Several separate detector hits (e.g. "verse 1" then later "verse 2",
  each its own reference with its own real Whisper timestamp) keep
  their real timestamps untouched — nothing is estimated.
- One reference covering a spoken range ("verse 1 to 2" said once) has
  exactly one real timestamp, for verse 1. Verse 2 has no real moment to
  anchor to, so its `display_at` is estimated from reading pace
  (`words_per_minute`, default 150, floored at `min_gap_seconds`).

Every `VerseEvent.timing_source` is `"real"` or `"estimated"` — check it
rather than assuming.

Use `--with-text` on any CLI mode to resolve and print verse text, paced
by this logic (`--wpm` to change the reading-pace estimate). `--json`
then includes a `verse_events` array alongside `references`.

## CLI
```
python scripture_detector/cli.py text "Turn to 2 John chapter 1 verse 3 to 8"
python scripture_detector/cli.py file transcript.txt
python scripture_detector/cli.py audio                # transcribes for_whisper (sermon.mp3)
python scripture_detector/cli.py audio other.mp3 --model base
python scripture_detector/cli.py record --seconds 30  # mic -> test.wav -> transcribe -> detect
```
Add `--json out.json` to save results and `--show-transcript` to see the
timestamped Whisper segments plus each raw match. Audio modes call
`ScriptureDetector.detect_segments`, which joins the segments into one
text (so a reference split across a segment boundary still matches) and
maps each match back to the segment where it begins.

`cli.py` imports `record_audio.py` from the parent folder, so keep
`scripture_detector/` inside `OpenVerse/`. The included `record_audio.py`
is your original with `transcribe_audio()` now returning the Whisper
result, and `record_audio()` / `transcribe_audio()` accepting optional
seconds/filename/model arguments (defaults unchanged).