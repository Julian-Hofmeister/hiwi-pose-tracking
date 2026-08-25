"""Single-slot latest-frame buffer. Older unread frames are dropped."""

from __future__ import annotations

import threading
from typing import Generic, TypeVar

T = TypeVar('T')


class LatestFrameSlot(Generic[T]):
    """Hold at most one unprocessed item. ``put`` overwrites a waiting item."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._item: T | None = None
        self._event = threading.Event()
        self.dropped = 0

    def put(self, item: T) -> None:
        with self._lock:
            if self._item is not None:
                self.dropped += 1
            self._item = item
            self._event.set()

    def take(self, timeout: float | None = None) -> T | None:
        if not self._event.wait(timeout):
            return None
        with self._lock:
            item = self._item
            self._item = None
            self._event.clear()
            return item
