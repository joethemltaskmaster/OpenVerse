"""Operator window. Owns no playback state. Emits intent signals."""
from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class OperatorWindow(QWidget):
    request_start = Signal()
    request_pause = Signal()
    request_next = Signal()
    request_previous = Signal()
    request_restart = Signal()
    request_clear = Signal()
    approve_event = Signal(object)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("OpenVerse — Operator")
        self.resize(480, 560)

        t1 = QHBoxLayout()
        self._prev_btn = QPushButton("◀ Prev")
        self._next_btn = QPushButton("Next ▶")
        self._prev_btn.clicked.connect(self.request_previous)
        self._next_btn.clicked.connect(self.request_next)
        t1.addWidget(self._prev_btn)
        t1.addWidget(self._next_btn)

        t2 = QHBoxLayout()
        self._start_btn = QPushButton("Start")
        self._pause_btn = QPushButton("Pause")
        self._restart_btn = QPushButton("Restart")
        self._clear_btn = QPushButton("Clear screen")
        self._start_btn.clicked.connect(self.request_start)
        self._pause_btn.clicked.connect(self.request_pause)
        self._restart_btn.clicked.connect(self.request_restart)
        self._clear_btn.clicked.connect(self.request_clear)
        for b in (self._start_btn, self._pause_btn, self._restart_btn, self._clear_btn):
            t2.addWidget(b)

        self._auto_mode = QCheckBox("Auto-run (skip approval)")
        self._auto_mode.setChecked(False)

        self._queue_label = QLabel("Pending (waiting for approval):")
        self._queue = QListWidget()
        self._approve_btn = QPushButton("Approve selected")
        self._approve_btn.clicked.connect(self._approve_selected)
        self._queue.itemDoubleClicked.connect(lambda _: self._approve_selected())
        self._status = QLabel("Ready.")

        layout = QVBoxLayout(self)
        layout.addLayout(t1)
        layout.addLayout(t2)
        layout.addWidget(self._auto_mode)
        layout.addSpacing(16)
        layout.addWidget(self._queue_label)
        layout.addWidget(self._queue, stretch=1)
        layout.addWidget(self._approve_btn)
        layout.addWidget(self._status)

        self._pending: list = []

    def is_auto_run(self) -> bool:
        return self._auto_mode.isChecked()

    def enqueue(self, event) -> None:
        self._pending.append(event)
        preview = event.text[:60] + ("…" if len(event.text) > 60 else "")
        self._queue.addItem(
            f"{event.book} {event.chapter}:{event.verse} — {preview}"
        )
        self._status.setText(f"{len(self._pending)} pending approval")

    def set_status(self, text: str) -> None:
        self._status.setText(text)

    def set_playing(self, playing: bool) -> None:
        self._start_btn.setEnabled(not playing)
        self._pause_btn.setEnabled(playing)

    def _approve_selected(self) -> None:
        idx = self._queue.currentRow()
        if idx < 0 or idx >= len(self._pending):
            return
        event = self._pending.pop(idx)
        self._queue.takeItem(idx)
        self.approve_event.emit(event)
        self._status.setText(f"{len(self._pending)} pending approval")