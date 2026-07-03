from __future__ import annotations

import io
import json
import zipfile
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .channels import ChannelKind, ChannelRegistry
from .markers import MarkerStore


@dataclass
class ReplaySession:
    registry: ChannelRegistry
    markers: MarkerStore
    meta: dict
    raw_log: str = ""


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
