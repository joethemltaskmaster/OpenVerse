"""
playback/controller.py

Pure-Python playback clock for a List[VerseEvent]. No GUI imports. No
threads. Caller drives time via tick(); position is recomputed from a
monotonic baseline on every tick, so no drift accumulates.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable, List, Optional


@dataclass
class PlaybackState:
    loaded: bool = False
    playing: bool = False
    finished: bool = False
    index: int = -1


class PlaybackController:
    def __init__(self, events: Optional[List] = None):
        self._events: List = []
        self._state = PlaybackState()
        self._started_at: float = 0.0
        self._paused_at: float = 0.0
        self._on_show: List[Callable[[object], None]] = []
        self._on_finished: List[Callable[[], None]] = []
        if events:
            self.load(events)

    def add_on_show(self, cb): self._on_show.append(cb)
    def add_on_finished(self, cb): self._on_finished.append(cb)

    def load(self, events: List) -> None:
        self._validate(events)
        self._events = sorted(events, key=lambda e: e.display_at)
        self._state = PlaybackState(loaded=bool(events), index=-1)
        self._started_at = 0.0
        self._paused_at = 0.0

    def append(self, events: List) -> None:
        if not events:
            return
        self._validate(events)
        self._events.extend(events)
        self._events.sort(key=lambda e: e.display_at)
        self._state.loaded = True

    def clear(self) -> None:
        self._events = []
        self._state = PlaybackState()
        self._started_at = 0.0
        self._paused_at = 0.0

    def start(self) -> None:
        if not self._events or self._state.playing:
            return
        if self._state.finished or self._state.index == -1:
            self._paused_at = 0.0
            self._state.index = -1
        self._state.playing = True
        self._state.finished = False
        self._started_at = time.monotonic() - self._paused_at

    def play(self) -> None: self.start()

    def pause(self) -> None:
        if not self._state.playing:
            return
        self._paused_at = self._position()
        self._state.playing = False

    def restart(self) -> None:
        self._paused_at = 0.0
        self._state.index = -1
        self._state.finished = False
        self._state.playing = True
        self._started_at = time.monotonic()

    def next(self) -> None:
        if not self._events:
            return
        nxt = self._state.index + 1
        if nxt >= len(self._events):
            self._finish()
            return
        self._jump_to(nxt)

    def previous(self) -> None:
        if not self._events:
            return
        self._jump_to(max(self._state.index - 1, 0))

    def tick(self) -> None:
        if not self._state.playing or not self._events:
            return
        pos = self._position()
        target = -1
        for i, e in enumerate(self._events):
            if pos >= e.display_at:
                target = i
            else:
                break
        if target == -1:
            return
        if target != self._state.index:
            self._state.index = target
            self._emit_show(self._events[target])
        last = self._events[-1]
        finish_at = last.display_at + (last.duration_estimate or 0.0)
        if pos >= finish_at:
            self._finish()

    def state(self) -> PlaybackState:
        return PlaybackState(**self._state.__dict__)

    @staticmethod
    def _validate(events: List) -> None:
        for e in events:
            if not hasattr(e, "display_at"):
                raise ValueError("event missing display_at")
            if not hasattr(e, "duration_estimate"):
                raise ValueError("event missing duration_estimate")

    def _position(self) -> float:
        if not self._state.playing:
            return self._paused_at
        return time.monotonic() - self._started_at

    def _jump_to(self, index: int) -> None:
        self._state.index = index
        target_time = self._events[index].display_at
        self._paused_at = target_time
        if self._state.playing:
            self._started_at = time.monotonic() - target_time
        self._emit_show(self._events[index])

    def _emit_show(self, event) -> None:
        for cb in self._on_show:
            cb(event)

    def _finish(self) -> None:
        self._state.playing = False
        self._state.finished = True
        for cb in self._on_finished:
            cb()