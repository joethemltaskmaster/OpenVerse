"""
ui/detection_worker.py — QThread bridge. No detection logic inside.
Injected: transcribe_fn, detect_text_fn, detect_segments_fn.
"""
from __future__ import annotations

import logging
import os
import tempfile
import wave
from typing import Callable, Optional

import pyaudio
from PySide6.QtCore import QThread, Signal

from ui.transcript_adapter import normalize_transcript_result

log = logging.getLogger(__name__)

_FORMAT = pyaudio.paInt16
_CHANNELS = 1
_RATE = 44100
_CHUNK = 1024
_CHUNK_SECONDS = 8


class DetectionWorker(QThread):
    references_detected = Signal(list)
    error = Signal(str)
    stopped = Signal()

    def __init__(
        self,
        transcribe_fn: Callable[[str], object],
        detect_text_fn: Callable[[str], list],
        detect_segments_fn: Callable[[list], list],
        audio_source: Optional[str] = None,
        chunk_seconds: int = _CHUNK_SECONDS,
    ):
        super().__init__()
        self._transcribe = transcribe_fn
        self._detect_text = detect_text_fn
        self._detect_segments = detect_segments_fn
        self._source = audio_source
        self._chunk_seconds = chunk_seconds
        self._stop = False

    def stop(self) -> None:
        self._stop = True

    def run(self) -> None:
        try:
            if self._source:
                self._run_file(self._source)
            else:
                self._run_mic()
        except Exception as exc:
            log.exception("DetectionWorker crashed")
            self.error.emit(str(exc))
        finally:
            self.stopped.emit()

    def _run_file(self, path: str) -> None:
        log.info("Transcribing %s", path)
        raw = self._transcribe(path)
        text, segments = normalize_transcript_result(raw)
        log.info("Transcript: %d chars, %d segments", len(text), len(segments or []))
        if self._stop:
            return
        refs = (self._detect_segments(segments) if segments
                else self._detect_text(text)) or []
        if refs:
            self.references_detected.emit(refs)

    def _run_mic(self) -> None:
        audio = pyaudio.PyAudio()
        stream = audio.open(format=_FORMAT, channels=_CHANNELS, rate=_RATE,
                            input=True, frames_per_buffer=_CHUNK)
        log.info("Mic recording started")
        try:
            while not self._stop:
                chunk = self._record_chunk(stream)
                if self._stop:
                    break
                tmp = self._write_temp_wav(chunk, audio)
                try:
                    raw = self._transcribe(tmp)
                finally:
                    try:
                        os.unlink(tmp)
                    except OSError:
                        pass
                text, _ = normalize_transcript_result(raw)
                if not text.strip():
                    continue
                refs = self._detect_text(text) or []
                if refs:
                    self.references_detected.emit(refs)
        finally:
            stream.stop_stream()
            stream.close()
            audio.terminate()

    def _record_chunk(self, stream) -> bytes:
        frames = []
        n = int(_RATE / _CHUNK * self._chunk_seconds)
        for _ in range(n):
            if self._stop:
                break
            frames.append(stream.read(_CHUNK, exception_on_overflow=False))
        return b"".join(frames)

    def _write_temp_wav(self, data: bytes, audio: pyaudio.PyAudio) -> str:
        fd, path = tempfile.mkstemp(suffix=".wav")
        os.close(fd)
        with wave.open(path, "wb") as wf:
            wf.setnchannels(_CHANNELS)
            wf.setsampwidth(audio.get_sample_size(_FORMAT))
            wf.setframerate(_RATE)
            wf.writeframes(data)
        return path