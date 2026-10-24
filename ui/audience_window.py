"""
ui/audience_window.py

Fullscreen scripture display. Auto-shrinks font to fit. Runs on screen
2 if attached, else primary.
"""
from __future__ import annotations

import logging
import os

from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QFont, QFontMetrics, QGuiApplication, QPixmap, QColor, QPainter
from PySide6.QtWidgets import QGraphicsOpacityEffect, QLabel, QVBoxLayout, QWidget

log = logging.getLogger(__name__)

_FONT_FAMILY = "Georgia"
_TEXT_COLOR = "#f4f1ea"
_ACCENT_COLOR = "#d8c48a"
_BG_COLOR = "#0b0d10"
_MIN_POINT = 24
_MAX_POINT = 180
_LOGO_PATH = r"C:\Users\Joseph\Desktop\OpenVerse\cac_logo.jpg"


class _TimingDot(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._color = QColor("#8a9099")
        self.setFixedSize(9, 9)

    def set_timing_source(self, src: str) -> None:
        if src == "real":
            self._color = QColor("#6fbf73")
        elif src == "estimated":
            self._color = QColor("#d8a34e")
        else:
            self._color = QColor("#8a9099")
        self.update()

    def paintEvent(self, _evt) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setBrush(self._color)
        p.setPen(Qt.NoPen)
        p.drawEllipse(0, 0, 9, 9)
        p.end()


class AudienceWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("OpenVerse — Audience")
        self.setStyleSheet(f"background-color: {_BG_COLOR};")
        self.setCursor(Qt.BlankCursor)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)

        self._reference_label = QLabel("")
        self._reference_label.setAlignment(Qt.AlignCenter)
        self._reference_label.setStyleSheet(
            f"color: {_ACCENT_COLOR}; letter-spacing: 6px;"
        )

        self._verse_label = QLabel("")
        self._verse_label.setAlignment(Qt.AlignCenter)
        self._verse_label.setWordWrap(True)
        self._verse_label.setStyleSheet(f"color: {_TEXT_COLOR};")

        self._opacity = QGraphicsOpacityEffect()
        self._verse_label.setGraphicsEffect(self._opacity)
        self._fade = QPropertyAnimation(self._opacity, b"opacity")
        self._fade.setDuration(600)
        self._fade.setEasingCurve(QEasingCurve.InOutQuad)

        self._logo = QLabel(self)
        self._logo_visible = os.path.exists(_LOGO_PATH)
        if self._logo_visible:
            pix = QPixmap(_LOGO_PATH)
            if not pix.isNull():
                self._logo.setPixmap(pix.scaledToHeight(73, Qt.SmoothTransformation))
                self._logo.setStyleSheet("background: transparent;")
            else:
                self._logo_visible = False
        self._logo.setFixedSize(0, 0)

        self._dot = _TimingDot(self)
        self._dot.setStyleSheet("background: transparent;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(80, 120, 80, 120)
        layout.addWidget(self._reference_label)
        layout.addSpacing(40)
        layout.addWidget(self._verse_label, stretch=1)

        self._current_event = None
        self._show_on_target_screen()

    def _show_on_target_screen(self) -> None:
        screens = QGuiApplication.screens()
        target = screens[1] if len(screens) >= 2 else screens[0]
        self.setGeometry(target.geometry())
        self.showFullScreen()

    def show(self, event) -> None:
        self._current_event = event
        self._reference_label.setText(
            f"{event.book.upper()} {event.chapter}:{event.verse}"
        )
        self._verse_label.setText(event.text)
        self._dot.set_timing_source(getattr(event, "timing_source", ""))
        self._apply_fit()
        self._fade.stop()
        self._opacity.setOpacity(0.0)
        self._fade.setStartValue(0.0)
        self._fade.setEndValue(1.0)
        self._fade.start()

    def clear(self) -> None:
        self._current_event = None
        self._reference_label.setText("")
        self._verse_label.setText("")
        self._dot.set_timing_source("")

    def _apply_fit(self) -> None:
        text = self._verse_label.text()
        if not text:
            return
        avail = self._verse_label.size()
        if avail.width() <= 0 or avail.height() <= 0:
            QTimer.singleShot(50, self._apply_fit)
            return
        lo, hi, best = _MIN_POINT, _MAX_POINT, _MIN_POINT
        while lo <= hi:
            mid = (lo + hi) // 2
            if self._fits(text, mid, avail):
                best = mid
                lo = mid + 1
            else:
                hi = mid - 1
        self._verse_label.setFont(QFont(_FONT_FAMILY, best))
        self._reference_label.setFont(QFont(_FONT_FAMILY, max(14, int(best * 0.4))))
        if best == _MIN_POINT and not self._fits(text, _MIN_POINT, avail):
            log.warning("Verse does not fit at min font: %s %s:%s",
                        self._current_event.book, self._current_event.chapter,
                        self._current_event.verse)

    def _fits(self, text: str, point: int, avail) -> bool:
        fm = QFontMetrics(QFont(_FONT_FAMILY, point))
        bound = fm.boundingRect(0, 0, avail.width(), avail.height(),
                                Qt.TextWordWrap | Qt.AlignCenter, text)
        return bound.height() <= avail.height() and bound.width() <= avail.width()

    def resizeEvent(self, evt) -> None:
        super().resizeEvent(evt)
        self._dot.move(self.width() - 30, 18)
        if self._logo_visible and self._logo.pixmap() is not None:
            self._logo.setFixedSize(self._logo.pixmap().width(),
                                    self._logo.pixmap().height())
            self._logo.move(18, 18)
        if self._current_event is not None:
            self._apply_fit()

    def keyPressEvent(self, evt) -> None:
        if evt.key() == Qt.Key_Escape:
            self.showNormal()
        else:
            super().keyPressEvent(evt)