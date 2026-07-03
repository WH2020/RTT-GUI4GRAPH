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
    display_name: str = ""
    unit: str = ""
    scale: float = 1.0
    offset: float = 0.0
    color: str = ""
    target: str = ""
    latest_value: float | str | None = None
    latest_time: float | None = None
    _times: np.ndarray = field(init=False, repr=False)
    _values: np.ndarray = field(init=False, repr=False)
    _start: int = field(default=0, init=False, repr=False)
    _count: int = field(default=0, init=False, repr=False)

    def __post_init__(self) -> None:
        self._times = np.empty(self.capacity, dtype=float)
        self._values = np.empty(self.capacity, dtype=float)
        if not self.display_name:
            self.display_name = self.key
        if not self.target:
            self.target = "status" if self.kind == ChannelKind.ENUM else "main"

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
        self.latest_time = t

    def series(self) -> tuple[list[float], list[float]]:
        times, values = self.series_arrays()
        return times.tolist(), values.tolist()

    def series_arrays(
        self,
        start_time: float | None = None,
        max_points: int | None = None,
    ) -> tuple[np.ndarray, np.ndarray]:
        if self._count == 0:
            return np.empty(0, dtype=float), np.empty(0, dtype=float)
        indexes = (self._start + np.arange(self._count)) % self.capacity
        if start_time is not None:
            times = self._times[indexes]
            first = int(np.searchsorted(times, start_time, side="left"))
            indexes = indexes[first:]
        if max_points is not None and len(indexes) > max_points:
            indexes = indexes[-max_points:]
        return self._times[indexes].copy(), self._values[indexes].copy()

    def display_series_arrays(
        self,
        start_time: float | None = None,
        max_points: int | None = None,
    ) -> tuple[np.ndarray, np.ndarray]:
        times, values = self.series_arrays(start_time, max_points)
        if self.kind == ChannelKind.NUMERIC:
            values = values * self.scale + self.offset
        return times, values

    @property
    def earliest_time(self) -> float | None:
        if self._count == 0:
            return None
        return float(self._times[self._start])

    def apply_config(self, config: dict) -> None:
        if "display_name" in config:
            self.display_name = str(config["display_name"] or self.key)
        if "unit" in config:
            self.unit = str(config["unit"] or "")
        if "scale" in config:
            self.scale = float(config["scale"])
        if "offset" in config:
            self.offset = float(config["offset"])
        if "color" in config:
            self.color = str(config["color"] or "")
        if "target" in config:
            target = str(config["target"] or self.target)
            if target in {"main", "status"}:
                self.target = target
        if "enabled" in config:
            self.enabled = bool(config["enabled"])

    def to_config(self) -> dict:
        return {
            "display_name": self.display_name,
            "unit": self.unit,
            "scale": self.scale,
            "offset": self.offset,
            "color": self.color,
            "target": self.target,
            "enabled": self.enabled,
        }


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

    def set_channel_config(self, key: str, **config) -> None:
        self._channels[key].apply_config(config)

    def channel_configs(self) -> dict[str, dict]:
        return {key: channel.to_config() for key, channel in self._channels.items()}

    def apply_channel_configs(self, configs: dict[str, dict]) -> None:
        for key, config in configs.items():
            if key in self._channels:
                self._channels[key].apply_config(config)

    def _ensure(self, key: str, kind: ChannelKind) -> Channel:
        channel = self._channels.get(key)
        if channel is None:
            channel = Channel(key=key, kind=kind, capacity=self._capacity)
            self._channels[key] = channel
        return channel
