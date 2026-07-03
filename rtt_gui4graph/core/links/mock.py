from __future__ import annotations

import math
import random
import time
from typing import Any

from ..link_base import Field, LinkBase, LinkState, register_link


class MockLink(LinkBase):
    def __init__(self) -> None:
        super().__init__()
        self._opened = False
        self._next_emit = 0.0
        self._period = 0.01
        self._index = 0
        self.sent: list[bytes] = []

    @classmethod
    def config_fields(cls) -> list[Field]:
        return [
            Field("rate_hz", "Rate (Hz)", "int", 100),
            Field("terminal", "Terminal", "int", 0),
        ]

    def open(self, config: dict[str, Any]) -> None:
        rate_hz = float(config.get("rate_hz", 100) or 100)
        self._period = 1.0 / max(1.0, rate_hz)
        self._next_emit = time.monotonic()
        self._opened = True
        self.state_changed.emit(LinkState.CONNECTED, "mock connected")

    def close(self) -> None:
        self._opened = False
        self.state_changed.emit(LinkState.CLOSED, "mock closed")

    def read(self, _max_bytes: int) -> bytes:
        if not self._opened:
            return b""
        now = time.monotonic()
        if now < self._next_emit:
            return b""
        self._next_emit = now + self._period
        self._index += 1
        phase = self._index / 15.0
        state = "TOE_STRIKE2" if self._index % 80 < 40 else "WAIT_QUIET"
        align = "FULL_LOCKED" if self._index % 120 < 90 else "SEARCHING"
        event = "sample" if self._index % 50 else "wait_quiet"
        wr_dps = int(170 + 40 * math.sin(phase) + random.uniform(-4, 4))
        wy_dps = int(150 + 30 * math.cos(phase / 1.7) + random.uniform(-3, 3))
        line = (
            "TAP RTT dev=0 "
            f"event={event} enabled=1 connected=1 align={align} state={state} "
            f"wr_dps={wr_dps} wy_dps={wy_dps} cross={self._index % 2} "
            "span=4 level=3 moving=35 peak=50 quiet=60\n"
        )
        return line.encode("utf-8")

    def send(self, data: bytes) -> int:
        self.sent.append(bytes(data))
        return len(data)


register_link("mock", MockLink)
