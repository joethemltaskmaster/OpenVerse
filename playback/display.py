"""playback/display.py — display contract. Two methods, nothing else."""
from typing import Protocol, runtime_checkable


@runtime_checkable
class Display(Protocol):
    def show(self, event) -> None: ...
    def clear(self) -> None: ...