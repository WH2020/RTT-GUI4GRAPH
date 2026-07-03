from __future__ import annotations

import time
from collections.abc import Callable

from .records import RawLine


class LineAssembler:
    """Convert RTT byte chunks into timestamped text lines."""

    def __init__(self, clock: Callable[[], float] | None = None) -> None:
        self._clock = clock or time.monotonic
        self._buffer = bytearray()
        self._terminal = 0
        self._pending_terminal_escape = False

    def feed(self, data: bytes) -> list[RawLine]:
        lines: list[RawLine] = []
        for byte in data:
            if byte == 0xFF:
                self._pending_terminal_escape = True
                continue
            if self._pending_terminal_escape:
                self._pending_terminal_escape = False
                if byte <= 0x0F and byte not in (0x0A, 0x0D):
                    self._terminal = byte
                    continue
                self._buffer.append(0xFF)
            if byte == 0x0A:
                lines.append(self._emit_line())
                continue
            self._buffer.append(byte)
        return lines

    def flush(self) -> RawLine | None:
        if self._pending_terminal_escape:
            self._buffer.append(0xFF)
            self._pending_terminal_escape = False
        if not self._buffer:
            return None
        return self._emit_line()

    def _emit_line(self) -> RawLine:
        raw = bytes(self._buffer)
        self._buffer.clear()
        if raw.endswith(b"\r"):
            raw = raw[:-1]
        text = raw.decode("utf-8", errors="replace")
        return RawLine(
            t=self._clock(),
            terminal=self._terminal,
            text=text,
            decode_error="\ufffd" in text,
        )
