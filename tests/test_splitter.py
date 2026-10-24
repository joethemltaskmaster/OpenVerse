from presentation.verse_splitter import split_long_verses
from scripture_detector.models import VerseEvent, ScriptureReference


def _event(text, display_at=0.0, duration=0.0):
    ref = ScriptureReference(book="John", chapter=3, verse_start=16)
    return VerseEvent(
        book="John", chapter=3, verse=16, text=text,
        display_at=display_at, timing_source="estimated",
        source_ref=ref, duration_estimate=duration,
    )


def test_short_verse_unchanged():
    e = _event("For God so loved the world.", 0.0, 3.0)
    assert split_long_verses([e]) == [e]


def test_splits_long_verse():
    text = " ".join(["word"] * 150) + "."
    out = split_long_verses([_event(text, 0.0, 60.0)], max_words_per_event=55)
    assert len(out) >= 3
    for piece in out:
        assert len(piece.text.split()) <= 60


def test_preserves_timeline():
    text = " ".join(["word"] * 120) + "."
    out = split_long_verses([_event(text, 10.0, 48.0)], max_words_per_event=55)
    assert out[0].display_at == 10.0
    total = sum(p.duration_estimate for p in out)
    assert abs(total - 48.0) < 1.5


def test_splits_at_sentence_boundary():
    text = "First here. Second here. Third here. Fourth here."
    out = split_long_verses([_event(text, 0.0, 10.0)], max_words_per_event=7)
    for piece in out:
        assert piece.text.strip().endswith(".")


def test_preserves_verse_number():
    text = " ".join(["word"] * 100) + "."
    out = split_long_verses([_event(text, 0.0, 40.0)])
    for piece in out:
        assert piece.verse == 16
        assert piece.book == "John"