"""
main.py — application entry point.
"""
from __future__ import annotations

import logging
import sys

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from lookup.verse_presenter import VersePresenter
from presentation.verse_splitter import split_long_verses
from lookup.version_lookup import VersionLookup
from playback.controller import PlaybackController
from ui.audience_window import AudienceWindow
from ui.operator_window import OperatorWindow
from ui.detection_worker import DetectionWorker

from scripture_detector.detector import ScriptureDetector
from transcription import transcribe_audio

log = logging.getLogger(__name__)

# Set to a file path for file mode; None = live mic.
AUDIO_SOURCE: str | None = None
# AUDIO_SOURCE = r"C:\Users\Joseph\Desktop\OpenVerse\sermon_1.mp3"


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    app = QApplication(sys.argv)

    presenter = VersePresenter(VersionLookup())
    controller = PlaybackController()
    audience = AudienceWindow()
    operator = OperatorWindow()
    operator.show()

    controller.add_on_show(audience.show)
    controller.add_on_finished(audience.clear)

    operator.request_start.connect(controller.start)
    operator.request_pause.connect(controller.pause)
    operator.request_next.connect(controller.next)
    operator.request_previous.connect(controller.previous)
    operator.request_restart.connect(controller.restart)
    operator.request_clear.connect(controller.clear)
    operator.approve_event.connect(lambda event: controller.append([event]))

    tick_timer = QTimer()
    tick_timer.timeout.connect(controller.tick)
    tick_timer.start(16)

    # --- detection: ONE detector per session ---
    detector = ScriptureDetector()

    def _transcribe(path: str):
        return transcribe_audio(
            filename=path, model_name="small", mode="auto", language="en",
        )

    worker = DetectionWorker(
        transcribe_fn=_transcribe,
        detect_text_fn=lambda text: detector.detect(text),
        detect_segments_fn=lambda segs: detector.detect_segments(segs),
        audio_source=AUDIO_SOURCE,
    )

    def on_refs(refs):
        events = presenter.expand(refs)
        events = split_long_verses(
            events,
            words_per_minute=presenter.words_per_minute,
            min_gap_seconds=presenter.min_gap_seconds,
            max_words_per_event=55,
        )
        if operator.is_auto_run():
            controller.append(events)
        else:
            for ev in events:
                operator.enqueue(ev)

    worker.references_detected.connect(on_refs)
    worker.error.connect(lambda msg: operator.set_status(f"Detection error: {msg}"))
    worker.stopped.connect(lambda: operator.set_status("Detection stopped."))
    worker.start()

    def shutdown():
        worker.stop()
        worker.wait(2000)

    app.aboutToQuit.connect(shutdown)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()