from __future__ import annotations

import io
import json
import zipfile
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .channels import ChannelKind, ChannelRegistry
from .csv_export import export_channels_csv
from .markers import MarkerStore
from .records import Event, LogLine, ParseIssue, Sample


@dataclass
class ReplaySession:
    registry: ChannelRegistry
    markers: MarkerStore
    meta: dict
    raw_log: str = ""


class RecordingSession:
    def __init__(self, capacity: int = 100_000) -> None:
        self._capacity = capacity
        self._registry = ChannelRegistry(capacity=capacity)
        self._raw_lines: list[str] = []
        self._meta: dict = {}
        self._is_recording = False
        self._is_stopped = False

    @property
    def is_recording(self) -> bool:
        return self._is_recording

    @property
    def is_stopped(self) -> bool:
        return self._is_stopped

    @property
    def registry(self) -> ChannelRegistry:
        return self._registry

    @property
    def meta(self) -> dict:
        return dict(self._meta)

    @property
    def raw_log(self) -> str:
        return "\n".join(self._raw_lines)

    def start(self, meta: dict | None = None) -> None:
        self._registry = ChannelRegistry(capacity=self._capacity)
        self._raw_lines = []
        self._meta = dict(meta or {})
        self._is_recording = True
        self._is_stopped = False

    def stop(self) -> None:
        if self._is_recording:
            self._is_recording = False
            self._is_stopped = True

    def ingest(self, records: list[Sample | Event | LogLine | ParseIssue]) -> None:
        if not self._is_recording:
            return
        for record in records:
            if isinstance(record, (Sample, Event)):
                self._registry.ingest(record)
            elif isinstance(record, LogLine):
                self._raw_lines.append(
                    f"{record.t:10.3f} T{record.terminal}: {record.text}"
                )
            elif isinstance(record, ParseIssue):
                self._raw_lines.append(
                    f"{record.t:10.3f} {record.severity} {record.reason} "
                    f"{record.key or '-'}: {record.sample_text}"
                )

    def has_data(self) -> bool:
        return bool(self._registry.channels() or self._raw_lines)


def save_rttcap(
    path: str | Path,
    registry: ChannelRegistry,
    markers: MarkerStore,
    meta: dict | None = None,
    raw_log: str = "",
) -> None:
    arrays: dict[str, np.ndarray] = {}
    channels = []
    for index, channel in enumerate(registry.channels()):
        times, values = channel.series_arrays()
        arrays[f"ch{index}_times"] = times
        arrays[f"ch{index}_values"] = values
        channels.append(channel.to_config() | {"key": channel.key, "kind": channel.kind.value})

    data_buffer = io.BytesIO()
    np.savez(data_buffer, **arrays)
    payload = {
        "version": 1,
        "meta": meta or {},
        "channels": channels,
        "markers": markers.to_json(),
    }
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("meta.json", json.dumps(payload, ensure_ascii=False, indent=2))
        archive.writestr("data.npz", data_buffer.getvalue())
        archive.writestr("raw.log", raw_log)


def load_rttcap(path: str | Path) -> ReplaySession:
    with zipfile.ZipFile(path, "r") as archive:
        payload = json.loads(archive.read("meta.json").decode("utf-8"))
        raw_log = archive.read("raw.log").decode("utf-8") if "raw.log" in archive.namelist() else ""
        data = np.load(io.BytesIO(archive.read("data.npz")))
        registry = ChannelRegistry()
        for index, config in enumerate(payload.get("channels", [])):
            key = str(config["key"])
            kind = ChannelKind(str(config.get("kind", "numeric")))
            channel = registry._ensure(key, kind)
            channel.apply_config(config)
            times = data[f"ch{index}_times"]
            values = data[f"ch{index}_values"]
            for t, value in zip(times.tolist(), values.tolist(), strict=False):
                channel.append(float(t), float(value), float(value))
    return ReplaySession(
        registry=registry,
        markers=MarkerStore.from_json(payload.get("markers", {})),
        meta=dict(payload.get("meta", {})),
        raw_log=raw_log,
    )


def infer_recording_format(path: str | Path, selected_filter: str = "") -> str:
    suffix = Path(path).suffix.lower()
    if suffix == ".csv" or "CSV" in selected_filter:
        return "csv"
    if suffix == ".json" or "JSON" in selected_filter:
        return "json"
    return "rttcap"


def save_recording(
    path: str | Path,
    session: RecordingSession,
    markers: MarkerStore,
    file_format: str,
) -> None:
    file_format = file_format.lower()
    if file_format == "rttcap":
        save_rttcap(path, session.registry, markers, session.meta, session.raw_log)
        return
    if file_format == "csv":
        export_channels_csv(path, session.registry)
        return
    if file_format == "json":
        save_recording_json(path, session, markers)
        return
    raise ValueError(f"unsupported recording format: {file_format}")


def save_recording_json(
    path: str | Path,
    session: RecordingSession,
    markers: MarkerStore,
) -> None:
    channels = []
    for channel in session.registry.channels():
        times, values = channel.series_arrays()
        channels.append(
            {
                "key": channel.key,
                "kind": channel.kind.value,
                "config": channel.to_config(),
                "times": times.tolist(),
                "values": values.tolist(),
            }
        )
    data = {
        "version": 1,
        "meta": session.meta,
        "channels": channels,
        "markers": markers.to_json(),
        "raw_log": session.raw_log,
    }
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2), "utf-8")
