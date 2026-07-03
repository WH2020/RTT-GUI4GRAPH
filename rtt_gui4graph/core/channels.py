from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

import numpy as np

from .records import Event, Sample


class ChannelKind(str, Enum):
    NUMERIC = "numeric"
    ENUM = "enum"


@dataclass
class Channel:
    key: str
    kind: ChannelKind
    capacity: int
    enabled: bool = False
    latest_value: float | str | None = None
    _times: np.ndarray = field(init=False, repr=False)
    _values: np.ndarray = field(init=False, repr=False)
    _start: int = field(default=0, init=False, repr=False)
    _count: int = field(default=0, init=False, repr=False)

    def __post_init__(self) -> None:
        self._times = np.empty(self.capacity, dtype=float)
        self._values = np.empty(self.capacity, dtype=float)

    def append(self, t: float, value: float, latest_value: float | str) -> None:
        if self._count < self.capacity:
            index = (self._start + self._count) % self.capacity
            self._count += 1
        else:
            index = self._start
            self._start = (self._start + 1) % self.capacity
        self._times[index] = t
        self._values[index] = value
        self.latest_value = latest_value

    def series(self) -> tuple[list[float], list[float]]:
        if self._count == 0:
            return [], []
        indexes = (self._start + np.arange(self._count)) % self.capacity
        return self._times[indexes].tolist(), self._values[indexes].tolist()


class ChannelRegistry:
    def __init__(self, capacity: int = 100_000) -> None:
        if capacity <= 0:
            raise ValueError("capacity must be positive")
        self._capacity = capacity
        self._channels: dict[str, Channel] = {}

    def ingest(self, record: Sample | Event) -> Channel:
        if isinstance(record, Sample):
            channel = self._ensure(record.channel, ChannelKind.NUMERIC)
            channel.append(record.t, record.value, record.value)
            return channel
        channel = self._ensure(record.channel, ChannelKind.ENUM)
        channel.append(record.t, float(record.ordinal), record.label)
        return channel

    def ingest_many(self, records: list[Sample | Event]) -> list[Channel]:
        changed: list[Channel] = []
        for record in records:
            changed.append(self.ingest(record))
        return changed

    def channel(self, key: str) -> Channel:
        return self._channels[key]

    def channels(self) -> list[Channel]:
        return list(self._channels.values())

    def enabled_channels(self) -> list[Channel]:
        return [channel for channel in self._channels.values() if channel.enabled]

    def set_enabled(self, key: str, enabled: bool) -> None:
        self._channels[key].enabled = enabled

    def _ensure(self, key: str, kind: ChannelKind) -> Channel:
        channel = self._channels.get(key)
        if channel is None:
            channel = Channel(key=key, kind=kind, capacity=self._capacity)
            self._channels[key] = channel
        return channel
