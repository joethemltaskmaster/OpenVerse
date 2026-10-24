"""Manual smoke test — plays verse events in the terminal. Ctrl-C exits."""
import time

from presentation.verse_presenter import VersePresenter
from presentation.verse_splitter import split_long_verses
from lookup.version_lookup import VersionLookup
from playback.controller import PlaybackController
from playback.console_display import ConsoleDisplay
from scripture_detector.models import ScriptureReference


def main() -> None:
    presenter = VersePresenter(VersionLookup())
    refs = [
        ScriptureReference(book="John", chapter=3, verse_start=16, verse_end=17),
        ScriptureReference(book="Psalms", chapter=23, verse_start=1),
    ]
    events = split_long_verses(presenter.expand(refs))

    controller = PlaybackController(events)
    display = ConsoleDisplay()
    controller.add_on_show(display.show)
    controller.add_on_finished(display.clear)
    controller.start()

    try:
        while True:
            controller.tick()
            time.sleep(0.05)
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()