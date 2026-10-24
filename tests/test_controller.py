import pytest
from dataclasses import dataclass
from playback.controller import PlaybackController


@dataclass
class E:
    display_at: float
    duration_estimate: float
    text: str = ""


@pytest.fixture
def fake_clock(monkeypatch):
    class Clock:
        t = 0.0
        def now(self): return self.t
        def advance(self, s): self.t += s
    c = Clock()
    monkeypatch.setattr("playback.controller.time.monotonic", c.now)
    return c


@pytest.fixture
def events():
    return [E(0.0, 5.0, "a"), E(5.0, 5.0, "b"), E(10.0, 3.0, "c")]


def test_first_event_shows_at_zero(fake_clock, events):
    c = PlaybackController(events)
    shown = []
    c.add_on_show(lambda e: shown.append(e))
    c.start(); c.tick()
    assert shown[-1].text == "a"


def test_advances_at_boundary(fake_clock, events):
    c = PlaybackController(events)
    shown = []
    c.add_on_show(lambda e: shown.append(e))
    c.start(); c.tick()
    fake_clock.advance(5.0); c.tick()
    assert shown[-1].text == "b"


def test_pause_freezes(fake_clock, events):
    c = PlaybackController(events)
    c.start(); c.tick()
    fake_clock.advance(3.0); c.tick()
    c.pause()
    fake_clock.advance(100.0); c.tick()
    assert c.state().index == 0


def test_resume_continues(fake_clock, events):
    c = PlaybackController(events)
    c.start(); c.tick()
    fake_clock.advance(3.0); c.pause()
    fake_clock.advance(100.0)
    c.start(); c.tick()
    fake_clock.advance(2.5); c.tick()
    assert c.state().index == 1


def test_next_skips(fake_clock, events):
    c = PlaybackController(events)
    c.start(); c.tick()
    c.next()
    assert c.state().index == 1


def test_previous_goes_back(fake_clock, events):
    c = PlaybackController(events)
    c.start(); c.tick()
    c.next(); c.next()
    c.previous()
    assert c.state().index == 1


def test_append_extends(fake_clock, events):
    c = PlaybackController(events)
    c.start(); c.tick()
    c.append([E(13.0, 4.0, "d")])
    fake_clock.advance(13.5); c.tick()
    assert c.state().index == 3


def test_finished_fires_once(fake_clock, events):
    c = PlaybackController(events)
    finished = []
    c.add_on_finished(lambda: finished.append(True))
    c.start()
    for _ in range(20):
        fake_clock.advance(1.0); c.tick()
    assert finished == [True]


def test_restart_from_finish(fake_clock, events):
    c = PlaybackController(events)
    c.start()
    for _ in range(20):
        fake_clock.advance(1.0); c.tick()
    c.restart(); c.tick()
    assert c.state().index == 0
    assert c.state().playing


def test_empty_noop(fake_clock):
    c = PlaybackController()
    c.start(); c.tick()
    c.next(); c.previous(); c.pause()
    assert c.state().index == -1