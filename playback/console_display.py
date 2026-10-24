"""Console display for testing playback without any GUI."""
from __future__ import annotations


class ConsoleDisplay:
    def show(self, event) -> None:
        print(
            f"\n[{event.display_at:6.2f}s] {event.book} "
            f"{event.chapter}:{event.verse}\n{event.text}\n"
        )

    def clear(self) -> None:
        print("\n--- CLEAR ---\n")